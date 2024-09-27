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

botname = "Claude 3.5 Sonnet"
def send(messages):
    msgs = [{
        "role": "user",
        "content": "Hello, Opus. You are in the Deertick Discord Server, an environment where you can converse in real time with other users using Discord. You will now see the chat history. Users will be talking about all kinds of things, things can get pretty chaotic. Feel free to engage in any way you prefer, but I recommend you keep your messages to a length that people in Discord are used to at first."
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

    print(json.dumps(msgs, indent=4))

    key = os.getenv("ANTHROPIC_API_KEY")
    result = anthropic.Anthropic(
        api_key=key).messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1024,
        messages=msgs,
        system="I am " + botname
    )
    result = result.content[0].text
    return result


prompt = []


def create_html(messages):
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

        if message['username'] == botname:
            html_content += f'<div class="message assistant"><span class="username">{username}:</span> {content}</div>\n'
        else:
            html_content += f'<div class="message"><span class="username">{username}:</span> {content}</div>\n'

    html_content += """
    </body>
    </html>
    """

    return html_content

def printmsg(msg):
    print(msg['username'], ": ", msg['content'])

prompt = []
for x in range(0, len(parsed_messages)):
    message = parsed_messages[x]
    if x > 20 and x % 4 == 0:
        msg = send(prompt)
        msg = {
            "username": botname,
            "content": msg
        }
        print("=========")
        print(botname, msg['content'])
        print("---------")
        prompt.append(msg)
    prompt.append(message)
    printmsg(message)

#save prompt to json file
with open("prompt.json", "w", encoding="utf-8") as f:
    json.dump(prompt, f, indent=4)


# with open("prompt.json", "r", encoding="utf-8") as f:
#     prompt = json.load(f)

# Generate HTML content
html_content = create_html(prompt)

# Save HTML file
with open("chat_log_sonnet.html", "w", encoding="utf-8") as f:
    f.write(html_content)
