"""RF001/RF002: busca AD somente para grupo administrativo autorizado."""
from src.auth.auth import auth_handler


def test_mock_search_ad_user_known_user():
    result = auth_handler.search_ad_user("joao.silva")
    assert result["exists"] is True
    assert result["username"] == "joao.silva"
    assert result["displayName"] == "João da Silva"
    assert result["email"] == "joao.silva@ebserh.gov.br"
    assert "UTI Adulto" in result["department"]


def test_mock_search_ad_user_dynamic_dotted_name():
    result = auth_handler.search_ad_user("carlos.eduardo")
    assert result["exists"] is True
    assert result["displayName"] == "Carlos Eduardo"


def test_mock_search_ad_user_not_found():
    result = auth_handler.search_ad_user("inexistentuser999")
    assert result["exists"] is False


def test_admin_ad_user_search_endpoint_authenticated(client, login):
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.get("/api/admin/ad-user-search/maria.souza", headers=headers)
    assert response.status_code == 200
    assert response.json()["displayName"] == "Maria Souza"


def test_admin_ad_user_search_endpoint_unauthorized(client):
    assert client.get("/api/admin/ad-user-search/joao.silva").status_code == 401


def test_admin_search_denied_without_it_group(client):
    token = auth_handler.create_access_token({
        "username": "admin", "role": "CHEFIA", "groups": ["Users"]
    })
    response = client.get("/api/admin/ad-user-search/maria.souza",
                          headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
