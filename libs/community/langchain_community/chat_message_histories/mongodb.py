import json
import logging
from typing import List

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    BaseMessage,
    message_to_dict,
    messages_from_dict,
)

logger = logging.getLogger(__name__)

DEFAULT_DBNAME = "chat_history"
DEFAULT_COLLECTION_NAME = "message_store"


class MongoDBChatMessageHistory(BaseChatMessageHistory):
    """Chat message history that stores history in MongoDB.

    Args:
        connection_string: connection string to connect to MongoDB
        session_id: arbitrary key that is used to store the messages
            of a single chat session.
        database_name: name of the database to use
        collection_name: name of the collection to use
        index_creation: bool for collection index-creation. By default index_creation is True
    """

    def __init__(
        self,
        connection_string: str,
        session_id: str,
        database_name: str = DEFAULT_DBNAME,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        index_creation:bool =True
    ):
        from pymongo import MongoClient, errors

        self.connection_string = connection_string
        self.session_id = session_id
        self.database_name = database_name
        self.collection_name = collection_name

        try:
            self.client: MongoClient = MongoClient(connection_string)
        except errors.ConnectionFailure as error:
            logger.error(error)

        self.db = self.client[database_name]
        self.collection = self.db[collection_name]
        if index_creation: 
            """
            Conditional Index Creation for collection
            """
            self.collection.create_index("SessionId")

    @property
    def messages(self) -> List[BaseMessage]:  # type: ignore
        """Retrieve the messages from MongoDB"""
        from pymongo import errors

        try:
            cursor = self.collection.find({"SessionId": self.session_id})
        except errors.OperationFailure as error:
            logger.error(error)

        if cursor:
            items = [json.loads(document["History"]) for document in cursor]
        else:
            items = []

        messages = messages_from_dict(items)
        return messages

    def add_message(self, message: BaseMessage) -> None:
        """Append the message to the record in MongoDB"""
        from pymongo import errors

        try:
            self.collection.insert_one(
                {
                    "SessionId": self.session_id,
                    "History": json.dumps(message_to_dict(message)),
                }
            )
        except errors.WriteError as err:
            logger.error(err)

    def clear(self) -> None:
        """Clear session memory from MongoDB"""
        from pymongo import errors

        try:
            self.collection.delete_many({"SessionId": self.session_id})
        except errors.WriteError as err:
            logger.error(err)
