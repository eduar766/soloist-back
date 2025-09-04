"""Numbering service for generating sequential numbers for invoices and other entities.
Handles number generation, formatting, and sequence management.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date
import re

from app.domain.models.base import InvoiceNumber, ValidationError, BusinessRuleViolation
from app.domain.models.invoice import InvoiceSettings


class NumberingService:
    """
    Domain service for managing sequential numbering systems.
    Handles invoice numbers, project codes, and other sequential identifiers.
    """

    def __init__(self):
        # Default numbering patterns
        self.default_patterns = {
            "invoice": "INV-{number:06d}",
            "project": "PRJ-{year}-{number:04d}",
            "task": "TSK-{number:05d}",
            "client": "CLI-{number:04d}"
        }
        
        # Reserved prefixes that cannot be used
        self.reserved_prefixes = ["SYS", "ADM", "TMP", "DEL", "ARC"]

    def generate_invoice_number(
        self,
        user_id: str,
        settings: InvoiceSettings,
        current_numbers: List[InvoiceNumber]
    ) -> InvoiceNumber:
        """
        Generate the next invoice number based on settings and existing numbers.
        """
        # Get the next number in sequence
        next_number = self._get_next_number_in_sequence(
            current_numbers,
            settings.number_prefix,
            settings.number_suffix
        )
        
        # Create the invoice number
        invoice_number = InvoiceNumber(
            prefix=settings.number_prefix,
            number=next_number,
            suffix=settings.number_suffix
        )
        
        # Validate the generated number
        self._validate_invoice_number(invoice_number)
        
        return invoice_number

    def generate_project_code(
        self,
        user_id: str,
        client_name: str,
        project_name: str,
        existing_codes: List[str],
        pattern: Optional[str] = None
    ) -> str:
        """
        Generate a unique project code.
        """
        if pattern:
            return self._generate_from_pattern(pattern, existing_codes)
        
        # Default project code generation
        client_code = self._generate_code_from_name(client_name, 3)
        project_code = self._generate_code_from_name(project_name, 3)
        year = str(datetime.now().year)[2:]  # Last 2 digits of year
        
        base_code = f"{client_code}-{project_code}-{year}"
        
        # Ensure uniqueness
        if base_code not in existing_codes:
            return base_code
        
        # Add sequence number if base code exists
        sequence = 1
        while f"{base_code}-{sequence:02d}" in existing_codes:
            sequence += 1
        
        return f"{base_code}-{sequence:02d}"

    def generate_task_number(
        self,
        project_id: int,
        existing_numbers: List[int],
        pattern: Optional[str] = None
    ) -> str:
        """
        Generate a task number within a project.
        """
        if pattern:
            return self._generate_from_pattern(pattern, [str(n) for n in existing_numbers])
        
        # Find the next available number
        next_number = 1
        if existing_numbers:
            next_number = max(existing_numbers) + 1
        
        return f"TSK-{next_number:05d}"

    def format_number(
        self,
        number: int,
        pattern: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format a number using a pattern with context variables.
        """
        context = context or {}
        
        # Add common context variables
        now = datetime.now()
        context.update({
            "number": number,
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "date": now.strftime("%Y%m%d")
        })
        
        try:
            return pattern.format(**context)
        except KeyError as e:
            raise ValidationError(f"Invalid pattern variable: {e}", "pattern")
        except ValueError as e:
            raise ValidationError(f"Invalid pattern format: {e}", "pattern")

    def validate_number_format(
        self,
        number_string: str,
        expected_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate and parse a number string format.
        """
        result = {
            "is_valid": False,
            "parsed_parts": {},
            "validation_errors": []
        }
        
        if not number_string:
            result["validation_errors"].append("Number string cannot be empty")
            return result
        
        # Basic format validation
        if len(number_string) > 50:
            result["validation_errors"].append("Number string too long (max 50 characters)")
        
        # Check for invalid characters
        if not re.match(r'^[A-Za-z0-9\-_]+$', number_string):
            result["validation_errors"].append("Number contains invalid characters (only letters, numbers, hyphens, and underscores allowed)")
        
        # Try to parse as invoice number format
        try:
            if '-' in number_string:
                parts = number_string.split('-')
                if len(parts) >= 2:
                    # Try to find numeric part
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            result["parsed_parts"]["prefix"] = '-'.join(parts[:i]) if i > 0 else ''
                            result["parsed_parts"]["number"] = int(part)
                            result["parsed_parts"]["suffix"] = '-'.join(parts[i+1:]) if i < len(parts) - 1 else ''
                            break
            elif number_string.isdigit():
                result["parsed_parts"]["number"] = int(number_string)
                result["parsed_parts"]["prefix"] = ''
                result["parsed_parts"]["suffix"] = ''
        except (ValueError, IndexError):
            result["validation_errors"].append("Unable to parse number format")
        
        # Validate against expected pattern if provided
        if expected_pattern and not result["validation_errors"]:
            if not self._matches_pattern(number_string, expected_pattern):
                result["validation_errors"].append(f"Number does not match expected pattern: {expected_pattern}")
        
        result["is_valid"] = len(result["validation_errors"]) == 0
        return result

    def create_numbering_sequence(
        self,
        sequence_name: str,
        pattern: str,
        starting_number: int = 1,
        increment: int = 1,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new numbering sequence configuration.
        """
        # Validate sequence name
        if not sequence_name or not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', sequence_name):
            raise ValidationError("Invalid sequence name format", "sequence_name")
        
        # Validate pattern
        if "{number" not in pattern:
            raise ValidationError("Pattern must contain {number} placeholder", "pattern")
        
        # Validate starting number
        if starting_number < 0:
            raise ValidationError("Starting number cannot be negative", "starting_number")
        
        # Validate increment
        if increment <= 0:
            raise ValidationError("Increment must be positive", "increment")
        
        sequence_config = {
            "name": sequence_name,
            "pattern": pattern,
            "current_number": starting_number,
            "increment": increment,
            "context": context or {},
            "created_at": datetime.utcnow().isoformat(),
            "last_generated": None
        }
        
        return sequence_config

    def get_next_in_sequence(
        self,
        sequence_config: Dict[str, Any]
    ) -> str:
        """
        Get the next number in a sequence and update the configuration.
        """
        current_number = sequence_config["current_number"]
        pattern = sequence_config["pattern"]
        context = sequence_config.get("context", {})
        
        # Format the number
        formatted_number = self.format_number(current_number, pattern, context)
        
        # Update sequence state
        sequence_config["current_number"] += sequence_config.get("increment", 1)
        sequence_config["last_generated"] = datetime.utcnow().isoformat()
        
        return formatted_number

    def reset_sequence(
        self,
        sequence_config: Dict[str, Any],
        new_starting_number: int
    ) -> None:
        """
        Reset a numbering sequence to a new starting number.
        """
        if new_starting_number < 0:
            raise ValidationError("Starting number cannot be negative", "starting_number")
        
        sequence_config["current_number"] = new_starting_number
        sequence_config["last_reset"] = datetime.utcnow().isoformat()

    def find_gaps_in_sequence(
        self,
        existing_numbers: List[int],
        start_range: int = 1,
        end_range: Optional[int] = None
    ) -> List[int]:
        """
        Find gaps in a number sequence.
        """
        if not existing_numbers:
            return []
        
        existing_numbers.sort()
        end_range = end_range or max(existing_numbers)
        
        gaps = []
        expected = start_range
        
        for num in existing_numbers:
            if num >= start_range:
                while expected < num:
                    gaps.append(expected)
                    expected += 1
                expected = num + 1
        
        return gaps

    def suggest_number_pattern(
        self,
        entity_type: str,
        organization_name: Optional[str] = None,
        include_date: bool = True,
        include_sequence: bool = True
    ) -> str:
        """
        Suggest a numbering pattern based on entity type and preferences.
        """
        patterns = {
            "invoice": [
                "INV-{year}-{number:04d}",
                "{org_code}-INV-{number:06d}",
                "INV{year}{month:02d}-{number:04d}"
            ],
            "project": [
                "PRJ-{year}-{number:04d}",
                "{org_code}-{year}-{number:03d}",
                "P{year}{month:02d}-{number:04d}"
            ],
            "client": [
                "CLI-{number:04d}",
                "{org_code}-C-{number:03d}",
                "CLIENT-{number:05d}"
            ],
            "task": [
                "TSK-{number:05d}",
                "T-{project_id}-{number:03d}",
                "TASK-{year}-{number:04d}"
            ]
        }
        
        entity_patterns = patterns.get(entity_type, ["ID-{number:04d}"])
        
        # Choose pattern based on preferences
        if organization_name and include_date:
            return entity_patterns[1] if len(entity_patterns) > 1 else entity_patterns[0]
        elif include_date:
            return entity_patterns[2] if len(entity_patterns) > 2 else entity_patterns[0]
        else:
            return entity_patterns[0]

    def _get_next_number_in_sequence(
        self,
        existing_numbers: List[InvoiceNumber],
        prefix: str,
        suffix: Optional[str]
    ) -> int:
        """
        Get the next number in sequence for invoice numbers.
        """
        # Filter numbers with matching prefix and suffix
        matching_numbers = [
            num.number for num in existing_numbers
            if num.prefix == prefix and num.suffix == suffix
        ]
        
        if not matching_numbers:
            return 1
        
        return max(matching_numbers) + 1

    def _validate_invoice_number(self, invoice_number: InvoiceNumber) -> None:
        """
        Validate an invoice number.
        """
        # Check for reserved prefixes
        if invoice_number.prefix.upper() in self.reserved_prefixes:
            raise ValidationError(
                f"Prefix '{invoice_number.prefix}' is reserved",
                "prefix"
            )
        
        # Validate the invoice number itself
        invoice_number.validate()

    def _generate_from_pattern(
        self,
        pattern: str,
        existing_values: List[str]
    ) -> str:
        """
        Generate a value from a pattern, ensuring uniqueness.
        """
        context = {
            "year": datetime.now().year,
            "month": datetime.now().month,
            "day": datetime.now().day,
            "number": 1
        }
        
        # Try different numbers until we find a unique one
        while True:
            try:
                value = pattern.format(**context)
                if value not in existing_values:
                    return value
                context["number"] += 1
            except KeyError as e:
                raise ValidationError(f"Invalid pattern variable: {e}", "pattern")

    def _generate_code_from_name(self, name: str, length: int = 3) -> str:
        """
        Generate a code from a name by taking initial letters.
        """
        if not name:
            return "XXX"[:length]
        
        # Remove special characters and split into words
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
        words = clean_name.split()
        
        if not words:
            return "XXX"[:length]
        
        # Take first letter of each word
        code = ''.join(word[0].upper() for word in words if word)
        
        # If code is too short, pad with first word
        if len(code) < length and words:
            first_word = words[0].upper()
            code += first_word[1:length-len(code)+1]
        
        return code[:length].ljust(length, 'X')

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """
        Check if a value matches a pattern (simplified implementation).
        """
        # This is a simplified pattern matching
        # In a real implementation, you'd want more sophisticated pattern matching
        try:
            # Try to see if the pattern could generate this value
            test_context = {
                "number": 1,
                "year": 2023,
                "month": 1,
                "day": 1
            }
            pattern.format(**test_context)
            return True
        except (KeyError, ValueError):
            return False