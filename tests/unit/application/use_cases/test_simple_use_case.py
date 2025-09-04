"""
Unit tests for simple use case patterns.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from app.application.use_cases.base_use_case import UseCaseResult


class TestUseCaseResult:
    """Test cases for UseCaseResult."""
    
    def test_success_result(self):
        """Test creating successful result."""
        result = UseCaseResult.success_result({"id": 1, "name": "test"})
        
        assert result.success is True
        assert result.data == {"id": 1, "name": "test"}
        assert result.error is None
        assert result.error_code is None
    
    def test_error_result(self):
        """Test creating error result."""
        result = UseCaseResult.error_result("Something went wrong", "TEST_ERROR")
        
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"
        assert result.error_code == "TEST_ERROR"
    
    def test_success_result_with_metadata(self):
        """Test success result with metadata."""
        metadata = {"execution_time": 0.1, "timestamp": "2024-01-01"}
        result = UseCaseResult.success_result({"data": "test"}, metadata)
        
        assert result.success is True
        assert result.metadata == metadata
    
    def test_error_result_with_metadata(self):
        """Test error result with metadata."""
        metadata = {"attempt": 1, "retry_after": 60}
        result = UseCaseResult.error_result("Error", "ERR_001", metadata)
        
        assert result.success is False
        assert result.metadata == metadata


# Simple mock repository for testing
class MockRepository:
    """Simple mock repository for testing use case patterns."""
    
    def __init__(self):
        self.data = {}
        self.next_id = 1
        self.should_fail = False
        self.fail_message = "Repository error"
    
    async def save(self, entity):
        """Mock save method."""
        if self.should_fail:
            raise Exception(self.fail_message)
        
        if not hasattr(entity, 'id') or entity.id is None:
            entity.id = self.next_id
            self.next_id += 1
        self.data[entity.id] = entity
        return entity
    
    async def find_by_id(self, entity_id):
        """Mock find by id method."""
        return self.data.get(entity_id)


# Simple entity for testing
class MockEntity:
    """Simple mock entity."""
    
    def __init__(self, name=None):
        self.id = None
        self.name = name
        self.owner_id = None


class TestMockRepository:
    """Test cases for mock repository."""
    
    @pytest.mark.asyncio
    async def test_save_new_entity(self):
        """Test saving a new entity."""
        repo = MockRepository()
        entity = MockEntity("test")
        
        saved = await repo.save(entity)
        
        assert saved.id == 1
        assert saved.name == "test"
        assert repo.data[1] == entity
    
    @pytest.mark.asyncio
    async def test_find_by_id(self):
        """Test finding entity by id."""
        repo = MockRepository()
        entity = MockEntity("test")
        await repo.save(entity)
        
        found = await repo.find_by_id(1)
        
        assert found == entity
        assert found.name == "test"
    
    @pytest.mark.asyncio
    async def test_find_non_existing(self):
        """Test finding non-existing entity."""
        repo = MockRepository()
        
        found = await repo.find_by_id(999)
        
        assert found is None
    
    @pytest.mark.asyncio
    async def test_repository_failure(self):
        """Test repository failure."""
        repo = MockRepository()
        repo.should_fail = True
        repo.fail_message = "Database connection failed"
        
        entity = MockEntity("test")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await repo.save(entity)


# Simple use case for testing patterns
class SimpleCreateEntityUseCase:
    """Simple use case for creating entities."""
    
    def __init__(self, repository: MockRepository):
        self.repository = repository
        self.current_user_id = "test-user-123"
    
    async def execute(self, name: str) -> UseCaseResult:
        """Execute the create entity use case."""
        try:
            # Basic validation
            if not name or not name.strip():
                return UseCaseResult.error_result("Name is required", "VALIDATION_ERROR")
            
            # Create entity
            entity = MockEntity(name.strip())
            entity.owner_id = self.current_user_id
            
            # Save entity
            saved_entity = await self.repository.save(entity)
            
            # Return success result
            return UseCaseResult.success_result({
                "id": saved_entity.id,
                "name": saved_entity.name,
                "owner_id": saved_entity.owner_id
            })
            
        except Exception as e:
            return UseCaseResult.error_result(str(e), "EXECUTION_ERROR")


class TestSimpleCreateEntityUseCase:
    """Test cases for simple create entity use case."""
    
    @pytest.mark.asyncio
    async def test_create_entity_success(self):
        """Test successful entity creation."""
        repo = MockRepository()
        use_case = SimpleCreateEntityUseCase(repo)
        
        result = await use_case.execute("Test Entity")
        
        assert result.success is True
        assert result.data["name"] == "Test Entity"
        assert result.data["id"] == 1
        assert result.data["owner_id"] == "test-user-123"
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_create_entity_validation_error(self):
        """Test entity creation with validation error."""
        repo = MockRepository()
        use_case = SimpleCreateEntityUseCase(repo)
        
        result = await use_case.execute("")  # Empty name
        
        assert result.success is False
        assert result.error == "Name is required"
        assert result.error_code == "VALIDATION_ERROR"
        assert result.data is None
    
    @pytest.mark.asyncio
    async def test_create_entity_whitespace_name(self):
        """Test entity creation with whitespace-only name."""
        repo = MockRepository()
        use_case = SimpleCreateEntityUseCase(repo)
        
        result = await use_case.execute("   ")  # Only whitespace
        
        assert result.success is False
        assert result.error == "Name is required"
        assert result.error_code == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_create_entity_repository_error(self):
        """Test entity creation with repository error."""
        repo = MockRepository()
        repo.should_fail = True
        repo.fail_message = "Database unavailable"
        
        use_case = SimpleCreateEntityUseCase(repo)
        
        result = await use_case.execute("Test Entity")
        
        assert result.success is False
        assert result.error == "Database unavailable"
        assert result.error_code == "EXECUTION_ERROR"
        assert result.data is None
    
    @pytest.mark.asyncio
    async def test_create_entity_trims_name(self):
        """Test that entity creation trims whitespace from name."""
        repo = MockRepository()
        use_case = SimpleCreateEntityUseCase(repo)
        
        result = await use_case.execute("  Test Entity  ")
        
        assert result.success is True
        assert result.data["name"] == "Test Entity"  # Trimmed
    
    @pytest.mark.asyncio
    async def test_multiple_entities_auto_increment(self):
        """Test creating multiple entities with auto-incrementing IDs."""
        repo = MockRepository()
        use_case = SimpleCreateEntityUseCase(repo)
        
        result1 = await use_case.execute("First Entity")
        result2 = await use_case.execute("Second Entity")
        
        assert result1.success is True
        assert result2.success is True
        assert result1.data["id"] == 1
        assert result2.data["id"] == 2
        assert result1.data["name"] == "First Entity"
        assert result2.data["name"] == "Second Entity"
    
    @pytest.mark.asyncio
    async def test_repository_state_persistence(self):
        """Test that repository maintains state between operations."""
        repo = MockRepository()
        use_case = SimpleCreateEntityUseCase(repo)
        
        # Create entity
        result = await use_case.execute("Test Entity")
        assert result.success is True
        entity_id = result.data["id"]
        
        # Verify it's in repository
        found = await repo.find_by_id(entity_id)
        assert found is not None
        assert found.name == "Test Entity"
        assert found.owner_id == "test-user-123"