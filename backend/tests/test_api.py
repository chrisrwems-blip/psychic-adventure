"""Tests for the API endpoints."""
import pytest


class TestHealth:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestProjects:
    def test_create_project(self, client):
        response = client.post("/api/projects/", json={
            "name": "Phoenix DC Module 3",
            "client": "Acme Corp",
            "location": "Phoenix, AZ",
            "tier_level": "III",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Phoenix DC Module 3"
        assert data["client"] == "Acme Corp"
        assert data["tier_level"] == "III"
        assert data["id"] > 0

    def test_list_projects(self, client):
        # Create two projects
        client.post("/api/projects/", json={"name": "Project A"})
        client.post("/api/projects/", json={"name": "Project B"})

        response = client.get("/api/projects/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_project(self, client):
        create_res = client.post("/api/projects/", json={"name": "Test Project"})
        project_id = create_res.json()["id"]

        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Test Project"

    def test_get_nonexistent_project(self, client):
        response = client.get("/api/projects/999")
        assert response.status_code == 404

    def test_delete_project(self, client):
        create_res = client.post("/api/projects/", json={"name": "To Delete"})
        project_id = create_res.json()["id"]

        response = client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 200

        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 404


class TestEquipmentTypes:
    def test_list_equipment_types(self, client):
        response = client.get("/api/reviews/equipment-types")
        assert response.status_code == 200
        types = response.json()["equipment_types"]
        assert "switchgear" in types
        assert "ups" in types
        assert "cooling" in types
        assert len(types) >= 12


class TestComments:
    def _create_project_and_submittal(self, client, db_session):
        """Helper to create a project and a submittal for comment testing."""
        from app.models.database_models import Project, Submittal
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        submittal = Submittal(
            project_id=project.id,
            title="Test Switchgear",
            equipment_type="switchgear",
            file_path="/tmp/test.pdf",
        )
        db_session.add(submittal)
        db_session.commit()
        db_session.refresh(submittal)
        return project.id, submittal.id

    def test_add_comment(self, client, db_session):
        _, submittal_id = self._create_project_and_submittal(client, db_session)

        response = client.post(f"/api/comments/submittal/{submittal_id}", json={
            "comment_text": "SCCR rating not found in submittal",
            "severity": "critical",
            "reference_code": "NEC 110.10",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["comment_text"] == "SCCR rating not found in submittal"
        assert data["severity"] == "critical"
        assert data["status"] == "open"

    def test_list_comments(self, client, db_session):
        _, submittal_id = self._create_project_and_submittal(client, db_session)

        client.post(f"/api/comments/submittal/{submittal_id}", json={"comment_text": "Comment 1", "severity": "critical"})
        client.post(f"/api/comments/submittal/{submittal_id}", json={"comment_text": "Comment 2", "severity": "minor"})

        response = client.get(f"/api/comments/submittal/{submittal_id}")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_filter_comments_by_severity(self, client, db_session):
        _, submittal_id = self._create_project_and_submittal(client, db_session)

        client.post(f"/api/comments/submittal/{submittal_id}", json={"comment_text": "Critical issue", "severity": "critical"})
        client.post(f"/api/comments/submittal/{submittal_id}", json={"comment_text": "Minor note", "severity": "minor"})

        response = client.get(f"/api/comments/submittal/{submittal_id}", params={"severity": "critical"})
        assert len(response.json()) == 1
        assert response.json()[0]["severity"] == "critical"

    def test_resolve_comment(self, client, db_session):
        _, submittal_id = self._create_project_and_submittal(client, db_session)

        create_res = client.post(f"/api/comments/submittal/{submittal_id}", json={"comment_text": "Fix this"})
        comment_id = create_res.json()["id"]

        response = client.patch(f"/api/comments/{comment_id}", json={
            "status": "resolved",
            "resolution_notes": "Fixed per vendor response",
        })
        assert response.status_code == 200
        assert response.json()["status"] == "resolved"
        assert response.json()["resolved_at"] is not None

    def test_defer_comment(self, client, db_session):
        _, submittal_id = self._create_project_and_submittal(client, db_session)

        create_res = client.post(f"/api/comments/submittal/{submittal_id}", json={"comment_text": "Defer this"})
        comment_id = create_res.json()["id"]

        response = client.patch(f"/api/comments/{comment_id}", json={"status": "deferred"})
        assert response.status_code == 200
        assert response.json()["status"] == "deferred"

    def test_delete_comment(self, client, db_session):
        _, submittal_id = self._create_project_and_submittal(client, db_session)

        create_res = client.post(f"/api/comments/submittal/{submittal_id}", json={"comment_text": "Delete me"})
        comment_id = create_res.json()["id"]

        response = client.delete(f"/api/comments/{comment_id}")
        assert response.status_code == 200

        response = client.get(f"/api/comments/submittal/{submittal_id}")
        assert len(response.json()) == 0


class TestEmails:
    def _setup(self, client, db_session):
        from app.models.database_models import Project, Submittal, ReviewComment
        project = Project(name="Email Test Project")
        db_session.add(project)
        db_session.commit()

        submittal = Submittal(
            project_id=project.id,
            title="UPS Submittal",
            equipment_type="ups",
            file_path="/tmp/test.pdf",
            contractor="ABC Electric",
            submittal_number="S-001",
        )
        db_session.add(submittal)
        db_session.commit()

        # Add some comments
        for text, severity in [
            ("SCCR not specified", "critical"),
            ("Battery runtime not documented", "major"),
            ("Color coding missing", "minor"),
        ]:
            db_session.add(ReviewComment(
                submittal_id=submittal.id,
                comment_text=text,
                severity=severity,
                reference_code="NEC 110.10",
            ))
        db_session.commit()
        return submittal.id

    def test_generate_rfi(self, client, db_session):
        submittal_id = self._setup(client, db_session)
        response = client.post(f"/api/emails/{submittal_id}/generate", json={
            "email_type": "rfi",
            "recipients": "vendor@example.com",
        })
        assert response.status_code == 200
        data = response.json()
        assert "RFI" in data["subject"]
        assert "CRITICAL" in data["body"]
        assert "ABC Electric" in data["body"]

    def test_generate_clarification(self, client, db_session):
        submittal_id = self._setup(client, db_session)
        response = client.post(f"/api/emails/{submittal_id}/generate", json={
            "email_type": "clarification",
        })
        assert response.status_code == 200
        assert "Clarification" in response.json()["subject"]

    def test_generate_rejection(self, client, db_session):
        submittal_id = self._setup(client, db_session)
        response = client.post(f"/api/emails/{submittal_id}/generate", json={
            "email_type": "rejection",
        })
        assert response.status_code == 200
        assert "Rejected" in response.json()["subject"]

    def test_generate_approval(self, client, db_session):
        submittal_id = self._setup(client, db_session)
        response = client.post(f"/api/emails/{submittal_id}/generate", json={
            "email_type": "approval",
        })
        assert response.status_code == 200
        assert "APPROVED" in response.json()["subject"]

    def test_list_emails(self, client, db_session):
        submittal_id = self._setup(client, db_session)
        client.post(f"/api/emails/{submittal_id}/generate", json={"email_type": "rfi"})
        client.post(f"/api/emails/{submittal_id}/generate", json={"email_type": "clarification"})

        response = client.get(f"/api/emails/submittal/{submittal_id}")
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestDashboard:
    def test_dashboard_empty(self, client):
        response = client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total_projects"] == 0
        assert data["total_submittals"] == 0
