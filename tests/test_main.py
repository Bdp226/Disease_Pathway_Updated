from main import calculate_text_overlap_similarity


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_get_all_diseases_empty(client):
    response = client.get("/diseases")
    assert response.status_code == 200
    assert response.json() == []

def test_get_disease_not_found(client):
    response = client.get("/diseases/nonexistent")
    assert response.status_code == 404


def test_unrelated_diseases_do_not_score_high_similarity():
    lung_cancer_text = (
        "lung cancer diagnosis treatment thoracic surgeon radiotherapy screening "
        "biomarker smoking recurrence ct scan tumor staging rehabilitation"
    )
    alzheimer_text = (
        "alzheimer dementia cognitive decline memory impairment amyloid diagnosis "
        "neurologist caregiver support behavior symptoms rehabilitation"
    )

    score = calculate_text_overlap_similarity(lung_cancer_text, alzheimer_text)
    assert score < 0.15
