import os
from dotenv import load_dotenv
import json
from collections import defaultdict
from datetime import datetime
from firebase_admin import credentials, firestore, initialize_app
import logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

FB_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS") # INCOMPLETE: NEED TO ADD FIREBASE CREDENTIALS PATH
if not FB_CREDENTIALS_JSON:
    raise RuntimeError("FIREBASE_CREDENTIALS is missing from environment variables")

# Load Firebase credentials from JSON file
try:
    FB_CREDENTIALS = json.loads(FB_CREDENTIALS_JSON)
except json.JSONDecodeError as e:
    raise ValueError(f"Invalid JSON format for FIREBASE_CREDENTIALS: {e}")

# Initialize Firebase app with credentials
cred = credentials.Certificate(FB_CREDENTIALS) 
firebase_app = initialize_app(cred)
db = firestore.client()

chats = db.collection("chats")

# NEED TO ADD "MESSAGE_ID" INPUT TO log_stats FUNCTION CALLED
def log_stat(chat_id: int, message_id: int, user_id: str, username: str, name: str, percent: int, timestamp: int):
    """
    Adds a message document to the "messages" subcollection of a chat document in Firestore.

    Parameters:
        chat_id (int):      The ID of the chat where the message was sent.
        message_id (int):   The ID of the message being logged.
        user_id (str):      The ID of the user who sent the message.
        username (str):     The username of the user who sent the message.
        name (str):         The name of the user who sent the message.
        percent (int):      The percentage of gayness to log.
        timestamp (int):    The timestamp of the message in seconds since epoch (Unix timestamp).

    Returns:
        None
    """
    try:
        # Get chat reference
        chat_ref = chats.document(str(chat_id))
        # if chat document reference does not exist, create document
        if not chat_ref.get().exists:
            chats.document(str(chat_id)).set({
                'chat_id': chat_id,
            })

        # Get chat's messages collection reference
        messages_ref = chat_ref.collection("messages")

        # Log message
        messages_ref.document(str(message_id)).set({
            'user_id': user_id,
            'percentage': percent,
            'timestamp': timestamp
        })

        # Upsert user info
        # Check if user already exists
        # if exists: check for last_update field and update if necessary
        user_ref = chat_ref.collection("users").document(str(user_id))
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            # Update user info if necessary
            if user_data.get('username') != user_id:
                user_ref.update({ 'username': username })
            if user_data.get('name') != user_id:
                user_ref.update({ 'name': name })
            # Update last_update if the new timestamp is greater
            if timestamp > user_data.get('last_update', 0): 
                user_ref.update({ 'last_update': timestamp })
        else:
            # Insert new document with last_update field
            user_ref.set({
                'username': username,
                'name': name,
                'last_update': timestamp,
            })

        logger.info(f"Logged message for user {user_id} in chat {chat_id} with percentage {percent}.")
    except Exception as e:
        logger.error(f"Failed to log message: {e}")

def bulk_log_stat(chat_id: int, messages: list, users: list):
    """
    Adds multiple messages to the "messages" subcollection of a chat document in Firestore.
    Adds multiple users to the "users" subcollection of a chat document in Firestore.
    """
    chat_ref = chats.document(str(chat_id))
    # if chat document reference does not exist, create document
    if not chat_ref.get().exists:
        chats.document(str(chat_id)).set({
            'chat_id': chat_id,
        })

    
    operations = []
    # process messages
    for message in messages:
        message_id = message.get('message_id')
        user_id = message.get('user_id')
        percent = message.get('percentage', -1)
        timestamp = message.get('timestamp', 0)

        msg_ref = chat_ref.collection("messages").document(str(message_id))

        operations.append(('set', msg_ref, {
            'user_id': user_id,
            'percentage': percent,
            'timestamp': timestamp
        }))

    # process users
    for user in users:
        user_id = user.get('user_id')
        username = user.get('username', 'Unknown')
        name = user.get('name', 'Unknown')
        last_update = user.get('last_update', 0)

        user_ref = chat_ref.collection("users").document(str(user_id))
        operations.append(('set', user_ref, {
            'username': username,
            'name': name,
            'last_update': last_update
        }, True))


    BATCH_LIMIT = 500
    try:
        for i in range(0, len(operations), BATCH_LIMIT):
            # Create a new batch for each chunk of operations
            batch = db.batch()

            for op in operations[i:i + BATCH_LIMIT]:
                if op[0] == 'set':
                    if len(op) == 3:
                        ref, data = op[1], op[2]
                        batch.set(ref, data)
                    elif len(op) == 4:
                        # If the operation includes a merge flag
                        ref, data, merge = op[1], op[2], op[3]
                        batch.set(ref, data, merge=merge)

            # Commit the batch write
            batch.commit()

        logger.info(f"Bulk logged {len(messages)} messages and {len(users)} users for chat {chat_id}.")
    except Exception as e:
        logger.error(f"Failed to bulk log messages/users: {e}")
        raise


def get_user_stats_all(chat_id: int, user_id: str):
    """"
    Retrieves a specific user's stats (Occurrences of each percentage) in a chat.

    Parameters:
        chat_id (int): The ID of the chat to retrieve stats from.
        user_id (str): The ID of the user to retrieve stats for.
    
    Returns:
        str: A formatted string of the user's percent counts or an error message.
    """""
    try:
        # Get chat reference
        chat_ref = chats.document(str(chat_id))
        # Check if chat document exists
        if not chat_ref.get().exists:
            logger.error(f"Chat with ID {chat_id} does not exist.")
            return "Chat not found."
        
        # Get chat's messages collection reference
        messages_ref = chat_ref.collection("messages")
        # Query messages from specified user
        query = messages_ref.where('user_id', '==', user_id)
        results = list(query.stream())

        # Check if any results were found
        if not results:
            logger.info(f"No messages found for user {user_id} in chat {chat_id}.")
            return "No stats yet!"

        # Count occurrences of each percentage
        percent_count = [0] * 101  # Initialize a list for percentages 0-100
        for doc in results:
            message = doc.to_dict()
            percent = message.get('percentage', -1)
            if 0 <= percent <= 100:
                percent_count[percent] += 1

        # Format the output
        logger.info(f"Retrieved percent counts for user {user_id} in chat {chat_id}.")
        return "\n".join([f"{p}% Gay: {percent_count[p]} times" for p in range(101)]) 
    except Exception as e:
        logger.error(f"Failed to retrieve user percent counts: {e}")
        return "Error retrieving stats."

def get_user_stats_nice(chat_id: int, user_id: str):
    """
    Retrieves a specific user's nice stats (Occurrence of specific "nice" percentage) in a chat.

    Parameters:
        chat_id (int): The ID of the chat to retrieve stats from.
        user_id (str): The ID of the user to retrieve stats for.

    Returns:
        str: A formatted string of the user's nice percent counts or an error message.
    """
    nice_percentages = {
        100: "💯 100% GAY 👨‍❤️‍💋‍👨",
        88:  "🐉 88% Huat Gay 🍀",
        69:  "☯️ 69% Gay 👯",
        0:   "🙅‍♂️ 0% Gay 🚫"
    }

    try:
        # Get chat reference
        chat_ref = chats.document(str(chat_id))
        if not chat_ref.get().exists:
            logger.error(f"Chat with ID {chat_id} does not exist.")
            return "Chat not found."
        
        # Get chat's messages collection reference
        messages_ref = chat_ref.collection("messages")
        # Query messages from specified user wih nice percentages
        query = messages_ref.where('user_id', '==', user_id).where('percentage', 'in', [0, 69, 88, 100])
        results = query.stream()

        # Check if any results were found
        if not results:
            logger.info(f"No nice stats found for user {user_id} in chat {chat_id}.")
            return "No nice stats yet!"
      

        # Count occurrences of each percentage and latest timestamp
        percent_count = defaultdict(int)  # Initialize a dictionary
        latest_timestamps = defaultdict(int)  # To track latest timestamp for each percentage
        for doc in results:
            message = doc.to_dict()
            percent = message.get('percentage', -1)

            # Only count if the percentage is one of the nice percentages
            if percent in nice_percentages:
                percent_count[percent] += 1 # increment count for this percentage

                # Update the latest timestamp for this percentage (Only for nice percentages)
                timestamp = message.get('timestamp', 0)
                if timestamp > latest_timestamps[percent]:
                    latest_timestamps[percent] = timestamp

        # Format the output
        output = []
        for target_percent in sorted(nice_percentages.keys(), reverse=True):
            if target_percent in percent_count:
                # Format latest timestamp for display
                formatted_time = datetime.fromtimestamp(latest_timestamps[target_percent]).strftime('%Y-%m-%d %H:%M')
                output.append(
                        f"{nice_percentages[target_percent]}\n→ {percent_count[target_percent]} times (last on {formatted_time})"
                    )

        return "\n\n".join(output)
    except Exception as e:
        logger.error(f"Failed to retrieve user nice percent counts: {e}")
        return "Error retrieving nice stats."
        
def get_leaderboard(chat_id: int):
    """
    Retrieves the leaderboard for a chat

    Parameters:
        chat_id (int): The ID of the chat to retrieve the leaderboard for.

    Returns:
        str: A formatted string of the leaderboard or an error message.
    """
    leaderboard_percents = {
        100: "💯The Great Gays 👨‍❤️‍💋‍👨100%",
        88: "🐉 88% Huat Gays 🍀",
        69: "☯️ 69 Gays 👯",
        0:  "🙅‍♂️ 0% Gays 🚫",
    }
    
    try:
        # Get chat reference
        chat_ref = chats.document(str(chat_id))
        if not chat_ref.get().exists:
            logger.error(f"Chat with ID {chat_id} does not exist.")
            return "Chat not found."
        
        # Get chat's messages collection reference
        messages_ref = chat_ref.collection("messages")
        # Aggregate counts of each percentage
        query = messages_ref.where('percentage', 'in', list(leaderboard_percents.keys()))
        results = query.stream()

        leaderboard = defaultdict(lambda: defaultdict(int))  # percentage -> user_id -> count
        relevant_users = set()  # To track users who have contributed to the leaderboard
        # Count occurrences of each user for each specific % category
        for doc in results:
            message = doc.to_dict()
            user_id = message.get('user_id')
            percent = message.get('percentage', -1)
            if percent in leaderboard_percents:
                leaderboard[percent][user_id] += 1
                relevant_users.add(user_id)

        # Get chats' users collection reference
        users_ref = chat_ref.collection("users")
        user_dict = {}  # To store user data for formatting
        for user_id in relevant_users:
            user_doc = users_ref.document(str(user_id)).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                username = user_data.get('username', '')
                name = user_data.get('name', '')

                # Use username if available, otherwise use name
                user_dict[user_id] = username if username else (name if name else 'Unknown')

        # Format the output
        output = []
        for percent in sorted(leaderboard_percents.keys(), reverse=True):
            users = leaderboard[percent]
            if users:
                # Append the header for this percentage
                output.append(leaderboard_percents[percent])

                # Sort users by their count in descending order
                # Append each user and their count
                for user_id in sorted(users.keys(), key=lambda uid: users[uid], reverse=True):
                    output.append(
                        f"@{user_dict.get(user_id, 'Unknown')} x{users[user_id]}"
                        )
                output.append("")

        if not output:
            logger.info(f"No leaderboard entries found for chat {chat_id}.")
            return "No leaderboard yet! Use @HowGayBot to start contributing your stats."
        
        # Compose output
        return "\n".join(output)

    except Exception as e:
        logger.error(f"Failed to retrieve leaderboard: {e}")
        return "Error retrieving leaderboard."

def get_last_update(chat_id: int):
    """
    Retrieves the last update timestamp for a specific chat.

    Parameters:
        chat_id (int): The ID of the chat to retrieve the last update for.

    Returns:
        int: The last update timestamp in seconds since epoch, or 0 if not found.
    """
    try:
        chat_ref = chats.document(str(chat_id))
        if not chat_ref.get().exists:
            logger.error(f"Chat with ID {chat_id} does not exist.")
            return 0
        
        # Get the last_update field from the chat document
        last_update = chat_ref.get().to_dict().get('last_update', 0)
        return last_update
    except Exception as e:
        logger.error(f"Failed to retrieve last update: {e}")
        return 0
    
def update_last_timestamp(chat_id: int, timestamp: int):
    """
    Updates the last update timestamp for a specific chat.

    Parameters:
        chat_id (int): The ID of the chat to update.
        timestamp (int): The new timestamp to set, in seconds since epoch.

    Returns:
        None
    """
    try:
        chat_ref = chats.document(str(chat_id))
        if not chat_ref.get().exists:
            logger.error(f"Chat with ID {chat_id} does not exist. Creating new chat document.")
            chats.document(str(chat_id)).set({'chat_id': chat_id})

        # Update the last_update field
        chat_ref.update({'last_update': timestamp})
        logger.info(f"Updated last timestamp for chat {chat_id} to {timestamp}.")
    except Exception as e:
        logger.error(f"Failed to update last timestamp: {e}")

def delete_chat_data(chat_id: int):
    """
    Deletes all data for a specific chat in Firestore.

    Parameters:
        chat_id (int): The ID of the chat to delete data for.

    Returns:
        None
    """
    try:
        chat_ref = chats.document(str(chat_id))
        if chat_ref.get().exists:

            messages_ref = chat_ref.collection("messages")
            users_ref = chat_ref.collection("users")
            # Delete all messages and users subcollections
            messages = messages_ref.stream()
            for message in messages:
                message.reference.delete()
            
            users = users_ref.stream()
            for user in users:
                user.reference.delete()

            # Finally, delete the chat document itself
            chat_ref.delete()
            logger.info(f"Deleted data for chat {chat_id}.")
        else:
            logger.warning(f"Chat with ID {chat_id} does not exist. No data to delete.")
    except Exception as e:
        logger.error(f"Failed to delete chat data: {e}")

# CHANGE THIS TO GET FROM SPECIFIC CHAT(?)
def get_chat_stats_all():
    """
    Retrieves all messages for all chats

    Parameters:
        None

    Returns:
        str: A formatted string of all chat stats or an error message.
    """
    try:
        all_chats = chats.stream()
        if not all_chats:
            logger.info("No stats found in any chat.")
            return "No stats yet!"

        output = []
        for chat in all_chats:
            chat_id = chat.id
            messages_ref = chat.collection("messages")
            messages = messages_ref.stream()

            for message in messages:
                msg_data = message.to_dict()
                user_id = msg_data.get('user_id', 'Unknown')
                percent = msg_data.get('percentage', -1)
                timestamp = msg_data.get('timestamp', 0)
                output.append(f"Chat: {chat_id}, User: {user_id}, Percentage: {percent}, Timestamp: {timestamp}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Failed to retrieve all stats: {e}")
        return "Error retrieving stats."

# CHANGE THIS TO GET FROM SPECIFIC CHAT(?)
def get_users_all():
    """
    Retrieves all users across all chats.

    Parameters:
        None

    Returns:
        str: A formatted string of all users or an error message.
    """
    try:
        all_chats = chats.stream()
        if not all_chats:
            logger.info("No users found in any chat.")
            return "No users found!"

        output = []
        for chat in all_chats:
            chat_id = chat.id
            users_ref = chat.collection("users")
            users = users_ref.stream()

            for user in users:
                user_data = user.to_dict()
                username = user_data.get('username', 'UNKNOWN')
                name = user_data.get('name', 'UNKNOWN')
                output.append(f"Chat: {chat_id}, User ID: {user.id}, Username: {username}, Name: {name}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Failed to retrieve all users: {e}")
        return "Error retrieving users."
    
# NEW
def get_user_last_update(chat_id: int, user_id: str):
    """
    Retrieves the last update timestamp for a specific user in a chat.

    Parameters:
        chat_id (int): The ID of the chat to retrieve the last update for.
        user_id (str): The ID of the user to retrieve the last update for.

    Returns:
        int: The last update timestamp in seconds since epoch, or 0 if not found.
    """
    try:
        # Get chat reference
        chat_ref = chats.document(str(chat_id))
        if not chat_ref.get().exists:
            logger.error(f"Chat with ID {chat_id} does not exist.")
            return 0
        
        # Get user's document reference
        user_ref = chat_ref.collection("users").document(str(user_id))
        user_doc = user_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            return user_data.get('last_update', 0)
        else:
            logger.warning(f"User {user_id} does not exist in chat {chat_id}.")
            return 0
    except Exception as e:
        logger.error(f"Failed to retrieve last update: {e}")
        return 0