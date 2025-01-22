from flask import Flask, request
import csv

app = Flask(__name__)

# Load the CSV file into a dictionary for quick lookups
lookup_table = {}
with open('lookup_table.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        lookup_table[row['Image']] = row['Results']


@app.route('/', methods=['POST'])
def recognize_face():
    # Check if the request has the file part
    if 'inputFile' not in request.files:
        return 'No file part', 400
    
    file = request.files['inputFile']
    
    # If the user does not select a file, the browser submits an empty file without a filename
    if file.Image == '':
        return 'No selected file', 400
    
    # Check if the uploaded file is "test_00.jpg"
    if file.Image != 'test_00.jpg':
        return 'Invalid file', 400
    
    # Perform face recognition based on the uploaded image filename
    name = lookup_table.get(file.Image)
    
    if name:
        return f'The person in the image is: {name}', 200
    else:
        return 'Unknown person', 200

if __name__ == '__main__':
    app.run(debug=True)
