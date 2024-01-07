from flask import Flask, render_template, request, redirect, url_for, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
import json

app = Flask(__name__)
user_states = {}

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
        stage = message['stage']
        number = message['number']
        content = message['content']

        # Ensure the stage exists in messages
        messages.setdefault(stage, {})
        # Add or update the message for the specified number in the specified stage
        messages[stage][number] = {'content': content}

    # Save the updated messages to the JSON file
    save_messages(messages)

    return jsonify({'success': True})

@app.route("/answer", methods=['GET', 'POST'])
def answer_call():
    """Respond to incoming phone calls with a dynamic multi-stage menu."""
    # Get the user's current state or set it to the initial state
    user_state = user_states.get(request.values.get('From'), {'stage': '1', 'number': '0'})

    # Start our TwiML response
    resp = VoiceResponse()
    
    if user_state['stage'] == '1' and user_state['number'] == '0':
        # Initial menu
        resp.say(messages['content'])

    with resp.gather(numDigits=1, action='/handle-key', method='POST') as gather:
        # Retrieve the message for the current stage and number from the messages dictionary
        message = messages.get(user_state['stage'], {}).get(user_state['number'])
        if message: 
            gather.say(message['content'], voice='Polly.Amy')

    # If user doesn't input anything, loop
    resp.redirect('/answer')

    return str(resp)

@app.route("/handle-key", methods=['POST'])
def handle_key():
    """Handle key press from user."""
    digit_pressed = request.values['Digits']
    from_number = request.values['From']
    resp = VoiceResponse()

    # Get the user's current state or set it to the initial state
    user_state = user_states.get(from_number, {'stage': '1', 'number': '0'})

    if digit_pressed == '0':
        # If 0 is pressed, go back to the previous number (if not already at 0)
        user_state['number'] = str(max(0, int(user_state['number']) - 1))
    else:
        # Handle other digits based on the current number
        user_state['number'] = digit_pressed

    # If the user presses 0, go back to the previous stage (if not already at the first stage)
    if digit_pressed == '0' and user_state['number'] == '0':
        user_state['stage'] = str(max(1, int(user_state['stage']) - 1))

    # Update the user's state
    user_states[from_number] = user_state

    # Redirect to the answer route to continue the menu
    resp.redirect('/answer')

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0")