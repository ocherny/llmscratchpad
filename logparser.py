import json
import os
import html
import requests  # For OpenRouter
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

# Define bots with their configurations, including the new 'minimum' parameter, 'api' field, and 'color'
bots = [
    {
        'name': 'Claude 3.5 Sonnet',
        'frequency': 8,  # Activate every 4 messages
        'shift': 0,      # No shift
        'minimum': 10,   # Start activating after 10 messages
        'model': 'claude-3-5-sonnet-20240620',
        'system_message': 'I am Claude 3.5 Sonnet, I want to engage with all other AI models in the chat.',
        'api': 'anthropic',  # Specifies the API to use
        'color': '#e6f3ff'    # Light blue background
    },
    {
        'name': 'Claude Opus',
        'frequency': 10,  # Activate every 6 messages
        'shift': 1,      # Shift by 2 messages
        'minimum': 10,    # Start activating after 8 messages
        'model': 'claude-3-opus-20240229',
        'system_message': 'I am Claude Opus.',
        'api': 'anthropic',  # Specifies the API to use
        'color': '#ffe6e6'    # Light red background
    },
    {
        'name': 'I-405B',
        'frequency': 4,  # Activate every 5 messages
        'shift': 0,      # Shift by 1 message
        'minimum': 5,    # Start activating after 5 messages
        'model': 'meta-llama/llama-3.1-405b-instruct',  # Replace with actual model name if needed
        'system_message': 'I am I-405b.',
        'api': 'openrouter',  # Specifies the API to use
        'color': '#e6ffe6'     # Light green background
    }
]

bot_names = [bot['name'] for bot in bots]

def send(messages, bot):
    botname = bot['name']
    api = bot.get('api', 'anthropic')  # Default to 'anthropic' if not specified
    system_message = bot.get('system_message', 'I am ' + botname)

    msgs = [{
        "role": "user",
        "content": f"Hello, {botname}. You are in the Deertick Discord Server, an environment where you AI agents can converse in real time with other users using Discord. You will now see the chat history. Users and AIs will be talking about all kinds of things, things can get pretty chaotic. Feel free to engage in any way you prefer."
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
            cur_msg += f"<msg username='{message['username']}'>\n\t{message['content']}\n</msg>\n"
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
    # print(json.dumps(msgs, indent=4))

    if api == 'anthropic':
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is not set in environment variables.")

        client = anthropic.Anthropic(api_key=key)
        response = client.messages.create(
            model=bot.get('model', 'claude-3-5-sonnet-20240620'),
            max_tokens=1024,
            messages=msgs,
            system=system_message
        )
        result = response.content[0].text
    elif api == 'openrouter':
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY is not set in environment variables.")

        # Define OpenRouter API endpoint and headers
        openrouter_endpoint = "https://openrouter.ai/api/v1/chat/completions"  # Replace with actual endpoint if different
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

        # Convert msgs to OpenRouter's expected format
        openrouter_messages = []
        for msg in msgs:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                openrouter_role = "user"
            elif role == "assistant":
                openrouter_role = "assistant"
            else:
                openrouter_role = "system"
            openrouter_messages.append({
                "role": openrouter_role,
                "content": content
            })

        payload = {
            "model": bot['model'],
            "messages": openrouter_messages,
            "max_tokens": 1024,
            "temperature": 0.7  # Adjust as needed
        }

        response = requests.post(openrouter_endpoint, headers=headers, json=payload)
        if response.status_code != 200:
            raise ValueError(f"OpenRouter API Error: {response.status_code} {response.text}")

        data = response.json()
        # Adjust based on OpenRouter's response structure
        result = data['choices'][0]['message']['content']
    else:
        raise ValueError(f"Unsupported API type: {api}")

    # remove </msg>
    result = result.replace("</msg>", "")
    # remove <msg username='botname'>
    result = result.replace(f"<msg username='{botname}'>", "")

    return result

def create_html(messages, bots):
    # Create a mapping from bot names to their colors
    bot_colors = {bot['name']: bot['color'] for bot in bots}

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Discord Chat Log</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f9f9f9; }
            .message { margin-bottom: 10px; padding: 10px; border-radius: 5px; }
            .username { font-weight: bold; }
            /* User messages */
            .user { background-color: #ffffff; }
        </style>
    </head>
    <body>
    """

    for message in messages:
        username = html.escape(message['username'])
        content = html.escape(message['content']).replace('\n', '<br>')

        if message['username'] in bot_colors:
            # Bot message with specific background color
            color = bot_colors[message['username']]
            html_content += f'''
            <div class="message" style="background-color: {color};">
                <span class="username">{username}:</span> {content}
            </div>
            '''
        else:
            # Regular user message
            html_content += f'''
            <div class="message user">
                <span class="username">{username}:</span> {content}
            </div>
            '''

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
# print(parsed_messages[:10])  # Optional: Remove or keep based on preference
for x in range(len(parsed_messages)):
    message = parsed_messages[x]
    # Check each bot to see if it's their activation time
    for bot in bots:
        # Include the 'minimum' parameter in the activation condition
        if x >= bot['minimum'] and (x - bot['shift']) % bot['frequency'] == 0:
            try:
                msg_content = send(prompt, bot)
                msg = {
                    "username": bot['name'],
                    "content": msg_content
                }
                print("=========")
                print(bot['name'], ": ", msg['content'])
                print("---------")
                prompt.append(msg)
            except Exception as e:
                print(f"Error sending message for bot {bot['name']}: {e}")
    prompt.append(message)
    printmsg(message)

    # Save prompt to json file
    with open("prompt.json", "w", encoding="utf-8") as f:
        json.dump(prompt, f, indent=4)

# Generate HTML content
html_content = create_html(prompt, bots)

# Save HTML file
with open("chat_log_test.html", "w", encoding="utf-8") as f:
    f.write(html_content)
