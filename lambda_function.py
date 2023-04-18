import boto3
import json
import logging
import random
from custom_encoder import CustomEncoder

logger = logging.get_logger()
logger.setLevel(logging.INFO)

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
    logger.info(event)
    # Extracting the http method
    httpMethod = event['httpMethod']
    path = event['path']

    # Takes the number of letters and creates a new game, returns the game id
    if httpMethod == postMethod and path == gamesPath:
        return startGame(json.loads(event['number_letters']))
    # Takes the guess, returns the number of attempts left and the words present
    elif httpMethod == postMethod and path == guessPath:
        response = saveGuess(event)

    elif httpMethod == getMethod and path == gamesPath:
        response = buildResponse(200)

    else:
        respose = buildResponse(404, 'Not Found')

    return response


def buildResponse(statusCode, body=None):
    response = {
        'statusCode': statusCode,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Controll-Allow-Origin': '*'
        }
    }

    if body is not None:
        response['body'] = json.dumps(body, cls=CustomEncoder)
    return response


def startGame(number_of_letters):
    # Parse the request body to get the number of letters
    num_letters = int(number_of_letters)

    # Generate a random target word of the specified length
    wordlist = ['apple', 'banana', 'cherry', 'date', 'elder', 'fig', 'grape', 'hazel', 'indigo', 'juniper', 'kiwi', 'lemon', 'mango',
                'nectar', 'orange', 'peach', 'quince', 'rasp', 'straw', 'tanger', 'ugli', 'vanilla', 'water', 'xigua', 'yellow', 'zucchini']
    target_word = random.choice([w for w in wordlist if len(w) == num_letters])

    # Create a new game record in DynamoDB
    game_id = str(uuid.uuid4())
    game_data = {'target_word': target_word, 'num_letters': num_letters,
                 'guesses': [], 'remaining_turns': num_letters+1}
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
    target_word = game_data['target_word']
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
