import logging
import datetime

from sqlalchemy import ForeignKey, Column, Integer, String, DateTime, JSON, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    email = Column(String, nullable=False)
    default_model = Column(Enum('default', 'gpt-3.5-turbo', 'gpt-3.5-turbo-0301'))
    created_time = Column(DateTime, nullable=False)
    last_login_time = Column(DateTime, nullable=True)
    preferences = Column(JSON, nullable=False)

    conversations = relationship('Conversation', back_populates='user')

class Conversation(Base):
    __tablename__ = 'conversation'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    title = Column(String, nullable=False)
    model = Column(Enum('default', 'gpt-3.5-turbo', 'gpt-3.5-turbo-0301'))
    created_time = Column(DateTime, nullable=False)
    updated_time = Column(DateTime, nullable=False)
    hidden = Column(Boolean, nullable=False)

    user = relationship('User', back_populates='conversations')
    messages = relationship('Message', back_populates='conversation')

class Message(Base):
    __tablename__ = 'message'

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('conversation.id'))
    role = Column(Enum('system', 'user', 'assistant'))
    message = Column(String, nullable=False)
    created_time = Column(DateTime, nullable=False)
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)

    conversation = relationship('Conversation', back_populates='messages')

class Orm:
    def __init__(self, database_uri):
        self.engine = create_engine(database_uri)
        session = sessionmaker(bind=self.engine)
        self.session = session()

        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
        self.logger = logging.getLogger(__name__)

    def add_user(self, username, password, email, default_model="default", preferences={}):
        now = datetime.datetime.now()
        user = User(username=username, password=password, email=email, default_model=default_model, created_time=now, last_login_time=now, preferences=preferences)
        self.session.add(user)
        self.session.commit()
        self.logger.info(f'Added User with username {username}')
        return user

    def add_conversation(self, user, title, model="default", hidden=False):
        now = datetime.datetime.now()
        conversation = Conversation(user_id=user.id, title=title, model=model, created_time=now, updated_time=now, hidden=False)
        self.session.add(conversation)
        self.session.commit()
        self.logger.info(f"Added Conversation with title '{title}' for User {user.username}")
        return conversation

    def add_message(self, conversation, role, message):
        now = datetime.datetime.now()
        message = Message(conversation_id=conversation.id, role=role, message=message, created_time=now, prompt_tokens=0, completion_tokens=0)
        self.session.add(message)
        self.session.commit()
        self.logger.info(f"Added Message with role '{role}' for Conversation with id {conversation.id}")
        return message

    def get_users(self):
        self.logger.info(f'Retrieving all Users')
        users = self.session.query(User).all()
        return users

    def get_user(self, user_id):
        self.logger.info(f'Retrieving User with id {user_id}')
        user = self.session.query(User).get(user_id)
        return user

    def get_conversations(self, user):
        self.logger.info(f'Retrieving Conversations for User with id {user.id}')
        conversations = user.conversations
        return conversations

    def get_messages(self, conversation):
        self.logger.info(f'Retrieving Messages for Conversation with id {conversation.id}')
        messages = conversation.messages
        return messages

