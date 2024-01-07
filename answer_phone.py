from flask import Flask, render_template, request, redirect, url_for, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
import json

app = Flask(__name__)

user_states = {}

level = []

MESSAGES_FILE = 'messages.json'

def load_messages():
    try:
        with open(MESSAGES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_messages(messages):
    with open(MESSAGES_FILE, 'w') as f:
        json.dump(messages, f, indent=2)

# Load messages from the JSON file
messages = load_messages()

@app.route("/")
def index():
    return render_template("index.html", messages=messages)

@app.route("/submit_messages", methods=['POST'])
def submit_messages():
    # Retrieve messages from the client-side
    client_messages = request.json.get('clientMessages', [])

    # Process and save the client messages as needed
    for message in client_messages:
        level = message['level']
        number = message['number']
        content = message['content']

        # Ensure the level exists in messages
        messages.setdefault(level, {})
        # Add or update the message for the specified number in the specified level
        messages[level][number] = {'content': content}

    # Save the updated messages to the JSON file
    save_messages(messages)

    return jsonify({'success': True})

@app.route("/answer", methods=['GET', 'POST'])
def answer_call():
    """Respond to incoming phone calls with a dynamic multi-level menu."""
    # Get the user's current state or set it to the initial state
    from_number = request.values.get('From')
    user_state = user_states.get(from_number, {'level': 0, 'attempts': 0})

    # Start our TwiML response
    resp = VoiceResponse()

    print(user_state['level'])

    if user_state['attempts'] >= 3:
        # End the call if the maximum number of attempts is reached
        resp.say("Thank you for calling. Goodbye.")
    else:
        if user_state['level'] == 0:
            # Initial menu
            resp.say(messages['content'])

        with resp.gather(numDigits=1, action='/handle-key', method='POST') as gather:
            message = None
            if user_state['level'] == 1:
                message = messages.get(f"{level[0]}", {})
            if user_state['level'] == 2:
                message = messages.get(f"{level[0]}", {}).get(f"{level[1]}", {})
            if user_state['level'] == 3:
                message = messages.get(f"{level[0]}", {}).get(f"{level[1]}", {}).get(f"{level[2]}", {})
            if message:
                gather.say(message['content'], voice='Polly.Amy')

        # If user doesn't input anything, increment the attempts counter
        resp.redirect('/answer')
        user_state['attempts'] += 1

    # Update the user's state
    user_states[from_number] = user_state

    return str(resp)

@app.route("/handle-key", methods=['POST'])
def handle_key():
    """Handle key press from user."""
    digit_pressed = request.values['Digits']
    from_number = request.values['From']
    resp = VoiceResponse()

    # Get the user's current state or set it to the initial state
    user_state = user_states.get(from_number, {'level': 0, 'attempts': 0})

    print(digit_pressed)

    if digit_pressed == '0':
        user_state['level'] -= 1
        level.pop()
    else:
        # user_state['level'] = str(max(1, int(user_state['level']) + 1))
        user_state['level'] += 1
        level.append(digit_pressed) 

    # Reset attempts counter on valid input
    user_state['attempts'] = 0

    # Update the user's state
    user_states[from_number] = user_state

    # Redirect to the answer route to continue the menu
    resp.redirect('/answer')

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0")
