from flask import Flask, jsonify, request, render_template
from openai import OpenAI
import anthropic
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# Game state
board = [['_', '_', '_'] for _ in range(3)]
current_player = 'X'
messages = []
player_ai = {'X': 'OpenAI', 'O': 'Anthropic'}
game_over = False

def print_board():
    return '\n'.join(['|'.join(row) for row in board])

def is_valid_move(row, col):
    return board[row][col] == '_'

def make_move(row, col):
    global current_player
    if is_valid_move(row, col):
        board[row][col] = current_player
        return True
    return False

def check_win():
    # Check rows and columns
    for i in range(3):
        if board[i][0] != '_' and board[i][0] == board[i][1] == board[i][2]:
            return True
        if board[0][i] != '_' and board[0][i] == board[1][i] == board[2][i]:
            return True
    # Check diagonals
    if board[0][0] != '_' and board[0][0] == board[1][1] == board[2][2]:
        return True
    if board[0][2] != '_' and board[0][2] == board[1][1] == board[2][0]:
        return True
    return False

def is_board_full():
    return all(cell != '_' for row in board for cell in row)

def switch_player():
    global current_player
    current_player = 'O' if current_player == 'X' else 'X'

def get_ai_move(player):
    prompt = f"""
You are playing Tic-Tac-Toe as player {player}. The current board state is:
'''
{print_board()}
'''
Provide your move as a row and column (both 0-indexed) in the format 'row,col'.
For example, '0,0' would be the top-left corner and '2,2' would be the bottom-right corner.
Choose a valid empty position '_'.
Try to win the game making a full line!
Think the best move to win faster!
If the opponent is about to win, try to avoid it!!
Also, provide a short message to your opponent (max 50 characters) in Brazilian Portuguese.
Respond in JSON format like this:
{{
    "move": "row,col",
    "message": "Your short message here"
}}
"""

    if player_ai[player] == 'OpenAI':
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are playing a game of Tic-Tac-Toe."},
                {"role": "user", "content": prompt}
            ]
        )
        ai_response = json.loads(response.choices[0].message.content.strip())
    elif player_ai[player] == 'Anthropic':
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=100,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        ai_response = json.loads(response.content[0].text.strip())
    elif player_ai[player] == 'Gemini':
        '''
        Listando modelos
            models/gemini-1.0-pro
            models/gemini-1.0-pro-001
            models/gemini-1.0-pro-latest
            models/gemini-1.0-pro-vision-latest
            models/gemini-1.5-flash
            models/gemini-1.5-flash-001
            models/gemini-1.5-flash-latest
            models/gemini-1.5-pro
            models/gemini-1.5-pro-001
            models/gemini-1.5-pro-latest
            models/gemini-pro
            models/gemini-pro-vision
        '''
        #modelo = "gemini-1.5-pro-001"
        modelo = "gemini-pro"
        model = genai.GenerativeModel(modelo)
        response = model.generate_content(prompt)
        ai_response = json.loads(response.text)

    print(f"Player {player} ({player_ai[player]}) response: {ai_response}")
    row, col = map(int, ai_response['move'].split(','))
    return row, col, ai_response['message']

@app.route('/')
def index():
    global board, current_player, messages, game_over
    return render_template('index.html', board=board, current_player=current_player, messages=messages, player_ai=player_ai, game_over=game_over)

@app.route('/play', methods=['POST'])
def play_turn():
    global board, current_player, messages, game_over

    if game_over:
        return jsonify({'error': 'Game is over. Please start a new game.'})

    row, col, message = get_ai_move(current_player)
    messages.append({"player": current_player, "message": message})

    if make_move(row, col):
        if check_win():
            result = f"Player {current_player} ({player_ai[current_player]}) wins!"
            messages.append({"player": "System", "message": result, "type": "system"})
            game_over = True
        elif is_board_full():
            result = "It's a draw!"
            messages.append({"player": "System", "message": result, "type": "system"})
            game_over = True
        else:
            switch_player()
            result = f"Player {current_player}'s turn"
    else:
        result = f"Invalid move by Player {current_player}, trying again"

    print(print_board())

    return jsonify({
        'board': board,
        'result': result,
        'current_player': current_player,
        'messages': messages,
        'player_ai': player_ai,
        'game_over': game_over
    })

@app.route('/set_ai', methods=['POST'])
def set_ai():
    global player_ai
    player = request.json['player']
    ai = request.json['ai']
    player_ai[player] = ai
    return jsonify({'success': True, 'player_ai': player_ai})

@app.route('/new_game', methods=['POST'])
def new_game():
    global board, current_player, messages, game_over
    board = [['_', '_', '_'] for _ in range(3)]
    current_player = 'X'
    messages = []
    game_over = False
    return jsonify({
        'board': board,
        'result': "New game started. Player X's turn",
        'current_player': current_player,
        'messages': messages,
        'player_ai': player_ai,
        'game_over': game_over
    })

if __name__ == '__main__':
    app.run(debug=True)