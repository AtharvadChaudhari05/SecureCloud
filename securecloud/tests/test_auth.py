def test_landing_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Context-Aware' in response.data

def test_register_page(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Register' in response.data

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data
