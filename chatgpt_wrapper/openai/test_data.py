import names
from rich.console import Console
from rich.markdown import Markdown
from chatgpt_wrapper.openai.orm import Base, Orm, User, Conversation, Message

console = Console()

orm = Orm('sqlite:////tmp/chatgpt-test.db')
Base.metadata.create_all(orm.engine)

# Create 5 Users
for i in range(5):
    username = names.get_full_name().lower().replace(" ", ".")
    password = 'password'
    email = f'{username}@example.com'
    user = orm.add_user(username, password, email)

    # Create 5 Conversations for each User
    for j in range(5):
        title = f'Conversation {j+1} for User {i+1}'
        conversation = orm.add_conversation(user, title)

        # Create 10 Messages for each Conversation
        for k in range(10):
            role = 'user' if k % 2 == 0 else 'assistant'
            message = f'This is message {k+1} in conversation {j+1} for user {i+1}'
            message = orm.add_message(conversation, role, message)

# Output the test data.
output = []
users = orm.get_users()
for user in users:
    conversations = orm.get_conversations(user)
    output.append(f'# User {user.id}: {user.username}, conversations: {len(conversations)}')
    for conversation in conversations:
        messages = orm.get_messages(conversation)
        output.append(f'### Conversation {conversation.id}: {conversation.title}, messages: {len(messages)}')
        for message in messages:
            output.append(f'* {message.role}: {message.message}')

console.print(Markdown("\n".join(output)))
