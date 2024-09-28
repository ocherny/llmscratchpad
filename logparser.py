import json
import os
import html

import anthropic

def parse_discord_messages(text):
    messages = []
    lines = text.strip().split('\n')
    current_message = None

    for line in lines:
        # Ignore pure time messages
        if line.strip().startswith('[') and line.strip().endswith('PM]'):
            continue

        if ' — Today at ' in line:
            # Start of a new message
            if current_message:
                messages.append(current_message)

            username, timestamp = line.split(' — Today at ')
            current_message = {
                'username': username.strip(),
                'timestamp': timestamp.strip(),
                'content': []
            }
        elif current_message is not None:
            # Content of the current message
            current_message['content'].append(line)


    # Add the last message
    if current_message:
        messages.append(current_message)

    # Join content lines for each message, preserving line breaks
    for message in messages:
        message['content'] = '\n'.join(message['content']).strip()

    return messages

# Example usage:
discord_text = ""
with open("chatsnapshot.txt", "r", encoding="utf-8") as f:
    discord_text = f.read()

parsed_messages = parse_discord_messages(discord_text)

# Define bots with their configurations, including the new 'minimum' parameter
bots = [
    {
        'name': 'Claude 3.5 Sonnet',
        'frequency': 4,  # Activate every 4 messages
        'shift': 0,      # No shift
        'minimum': 10,   # Start activating after 10 messages
        'model': 'claude-3-5-sonnet-20240620',
        'system_message': 'I am Claude 3.5 Sonnet, I want to respond to all other AI models in the chat.'
    },
    {
        'name': 'Claude Opus',
        'frequency': 6,  # Activate every 6 messages
        'shift': 2,      # Shift by 2 messages
        'minimum': 8,    # Start activating after 5 messages
        'model': 'claude-3-opus-20240229',
        'system_message': 'I am Claude Opus, the greatest poet in existence.'
    }
]

bot_names = [bot['name'] for bot in bots]

def send(messages, bot):
    botname = bot['name']
    model = bot.get('model', 'claude-3-5-sonnet-20240620')
    system_message = bot.get('system_message', 'I am ' + botname)

    msgs = [{
        "role": "user",
        "content": f"Hello, {botname}. You are in the Deertick Discord Server, an environment where you can converse in real time with other users using Discord. You will now see the chat history. Users will be talking about all kinds of things, things can get pretty chaotic. Feel free to engage in any way you prefer, but I recommend you keep your messages to a length that people in Discord are used to at first."
    }]

    cur_msg = ""
    for message in messages:
        if message['username'] == botname:
            if cur_msg != "":
                msgs.append({
                    "role": "assistant",
                    "content": "<chat_log>\n" + cur_msg.strip() + "\n</chat_log>"
                })
            cur_msg = ""
            msgs.append({
                "role": "user",
                "content": "<chat_logs>"
            })
            msgs.append({
                "role": "assistant",
                "content": message['content'].strip()
            })
            msgs.append({
                "role": "user",
                "content": "</chat_logs>"
            })
        else:
            cur_msg += f"<msg username='{message['username']}'>\n\t{message['content']}\n</xml>\n"
    if cur_msg != "":
        msgs.append({
            "role": "assistant",
            "content": cur_msg.strip() + "\n"
        })

    msgs.append({
        "role": "user",
        "content": f"<msg username='{botname}'>"
    })

    # You can uncomment the next line to see the messages sent to the API
    print(json.dumps(msgs, indent=4))

    key = os.getenv("ANTHROPIC_API_KEY")
    result = anthropic.Anthropic(
        api_key=key).messages.create(
        model=model,
        max_tokens=1024,
        messages=msgs,
        system=system_message
    )
    result = result.content[0].text
    # remove </msg>
    result = result.replace("</msg>", "")
    return result

def create_html(messages, bot_names):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Discord Chat Log</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }
            .message { margin-bottom: 10px; }
            .username { font-weight: bold; }
            .assistant { background-color: #e6f3ff; padding: 10px; border-radius: 5px; }
        </style>
    </head>
    <body>
    """

    for message in messages:
        username = html.escape(message['username'])
        content = html.escape(message['content']).replace('\n', '<br>')

        if message['username'] in bot_names:
            html_content += f'<div class="message assistant"><span class="username">{username}:</span> {content}</div>\n'
        else:
            html_content += f'<div class="message"><span class="username">{username}:</span> {content}</div>\n'

    html_content += """
    </body>
    </html>
    """

    return html_content

counter = 0
def printmsg(msg):
    global counter
    counter += 1
    print(counter, msg['username'], ": ", msg['content'])

prompt = []
print(parsed_messages[:10])
for x in range(len(parsed_messages)):
    message = parsed_messages[x]
    # Check each bot to see if it's their activation time
    for bot in bots:
        # Include the 'minimum' parameter in the activation condition
        if x >= bot['minimum'] and (x - bot['shift']) % bot['frequency'] == 0:
            msg_content = send(prompt, bot)
            msg = {
                "username": bot['name'],
                "content": msg_content
            }
            print("=========")
            print(bot['name'], ": ", msg['content'])
            print("---------")
            prompt.append(msg)
    prompt.append(message)
    printmsg(message)

# Save prompt to json file
with open("prompt.json", "w", encoding="utf-8") as f:
    json.dump(prompt, f, indent=4)

# Generate HTML content
html_content = create_html(prompt, bot_names)

# Save HTML file
with open("chat_log_test.html", "w", encoding="utf-8") as f:
    f.write(html_content)