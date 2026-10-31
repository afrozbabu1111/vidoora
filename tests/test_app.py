from app import app

def test_homepage():
    app.config['TESTING'] = True

    client = app.test_client()
    response = client.get('/')

    assert response.status_code == 200
