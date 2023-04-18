import boto3
import json
import random
import string
import logging


dynamodbTableName = 'wordle-game'
# Defining the dynamo cliet
dynamodb = boto3.resource('dynamodb')
# getting the table
table = dynamodb.Table(dynamodbTableName)

getMethod = 'GET'
postMethod = 'POST'

gamesPath = '/games'
game_idPath = '/games/-game-id-'
guessPath = '/games/-game-id-/guess'


def lambda_handler(event, context):
    try:
        # Extracting the http method
        httpMethod = event['httpMethod']
        path = event['path']

        # Takes the number of letters and creates a new game, returns the game id
        if httpMethod == postMethod and path == gamesPath:
            num_letters = json.loads(event['body'])
            response_json = json.dumps(startGame(num_letters['num_letters']))
            print(response_json)
            return {'statusCode': 201, 'body': response_json}

        # Return a 404 error for any other request
        return {'statusCode': 404, 'body': {'message': 'Resource not found'}}
    except Exception as e:
        # Log the error message
        print(f'Error: {str(e)}')
        # Return a 500 error with the error message
        return {'statusCode': 500, 'body': {'message': 'Internal server error'}}


def startGame(num_letters):
    # Parse the request body to get the number of letters
    num_letters = int(num_letters)
    # Generate a random target word of the specified length
    wordlist = ['apple', 'banana', 'cherry', 'date', 'elder', 'fig', 'grape', 'hazel', 'indigo', 'juniper', 'kiwi', 'lemon', 'mango',
                'nectar', 'orange', 'peach', 'quince', 'rasp', 'straw', 'tanger', 'ugli', 'vanilla', 'water', 'xigua', 'yellow', 'zucchini']

    # Generate a random word with the specified number of letter
    word = random.choice([w for w in wordlist if len(w) == num_letters])

    # Create a new game in DynamoDB
    game_id = str(random.randint(1, 1000000))
    game_data = {
        'word': word,
        'remaining_turns': int(num_letters)+1,
        'guesses': []
    }
    table.put_item(Item={'game_id': game_id, 'game_data': game_data})

    # Return the game ID
    return {'game_id': game_id}


def saveGuess(event):
    game_id = event['pathParameters']['game_id']
    guessed_word = event['body']['guessed_word'].lower()

    # Validate the guessed word
    if not guessed_word.isalpha() or len(guessed_word) != 5:
        return {'statusCode': 400, 'body': 'Invalid guessed word'}

    # Retrieve the game data from DynamoDB
    response = table.get_item(Key={'game_id': game_id})
    if 'Item' not in response:
        return {'statusCode': 404, 'body': 'Game not found'}
    game_data = response['Item']['game_data']

    # Check if the game is already over
    if game_data['remaining_turns'] == 0:
        return {'statusCode': 400, 'body': 'Game is already over'}

    # Check if the guessed word is the same as the target word
    target_word = game_data['word']
    if guessed_word == target_word:
        # If the guessed word is the same as the target word, mark it as correct
        feedback = 'correct'
    else:
        # Otherwise, mark each letter in the guessed word as either green, yellow, or gray
        feedback = []
        for i in range(len(guessed_word)):
            if guessed_word[i] == target_word[i]:
                feedback.append('green')
            elif guessed_word[i] in target_word:
                feedback.append('yellow')
            else:
                feedback.append('gray')

    # Add the guessed word to the list of guesses and decrement the remaining turns
    game_data['guesses'].append(guessed_word)
    game_data['remaining_turns'] -= 1

    # Update the game data in DynamoDB
    table.update_item(Key={'game_id': game_id}, UpdateExpression='SET game_data = :game_data',
                      ExpressionAttributeValues={':game_data': game_data})

    # Return the feedback for the guessed word
    return {'statusCode': 200, 'body': feedback}


def getGame(event):
    # Parse the request parameters to get the game ID
    game_id = event['pathParameters']['game_id']

    # Retrieve the game data from DynamoDB
    response = table.get_item(Key={'game_id': game_id})
    if 'Item' not in response:
        return {'statusCode': 404, 'body': 'Game not found'}
    game_data = response['Item']['game_data']

    # Return the game status
    response_body = {
        'remaining_turns': game_data['remaining_turns'],
        'guesses': game_data['guesses']
    }
    return {'statusCode': 200, 'body': response_body}
