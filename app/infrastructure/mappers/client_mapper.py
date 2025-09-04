"""
Client mapper for converting between domain entities and database models.
"""

import json
from typing import Optional

from app.domain.models.client import Client, ContactInfo, ClientStatus, PaymentTerms
from app.infrastructure.db.models import ClientModel


class ClientMapper:
    """Maps between Client domain entity and ClientModel database model."""
    
    def domain_to_model(self, client: Client) -> ClientModel:
        """Convert Client domain entity to ClientModel."""
        # Serialize contact info
        contact_data = client.contact.to_dict() if client.contact else None
        
        return ClientModel(
            id=client.id,
            owner_id=client.owner_id,
            name=client.name,
            contact_data=json.dumps(contact_data) if contact_data else None,
            tax_id=client.tax_id,
            company_type=client.company_type,
            industry=client.industry,
            default_currency=client.default_currency,
            default_hourly_rate=client.default_hourly_rate,
            payment_terms=client.payment_terms.value,
            custom_payment_terms=client.custom_payment_terms,
            notes=client.notes,
            tags=json.dumps(client.tags) if client.tags else "[]",
            status=client.status.value,
            total_projects=client.total_projects,
            active_projects=client.active_projects,
            total_invoiced=client.total_invoiced,
            total_paid=client.total_paid,
            outstanding_balance=client.outstanding_balance,
            created_at=client.created_at,
            updated_at=client.updated_at,
            version=client.version
        )
    
    def model_to_domain(self, model: ClientModel) -> Client:
        """Convert ClientModel to Client domain entity."""
        # Parse contact data JSON
        contact_info = None
        if model.contact_data:
            try:
                contact_data = json.loads(model.contact_data)
                contact_info = ContactInfo(**contact_data)
            except (json.JSONDecodeError, TypeError):
                contact_info = ContactInfo()
        else:
            contact_info = ContactInfo()
        
        # Parse tags JSON
        tags = []
        if model.tags:
            try:
                tags = json.loads(model.tags)
            except (json.JSONDecodeError, TypeError):
                tags = []
        
        client = Client(
            owner_id=model.owner_id,
            name=model.name,
            contact=contact_info,
            tax_id=model.tax_id,
            company_type=model.company_type,
            industry=model.industry,
            default_currency=model.default_currency or "USD",
            default_hourly_rate=model.default_hourly_rate,
            payment_terms=PaymentTerms(model.payment_terms) if model.payment_terms else PaymentTerms.NET_30,
            custom_payment_terms=model.custom_payment_terms,
            notes=model.notes,
            tags=tags,
            status=ClientStatus(model.status) if model.status else ClientStatus.ACTIVE,
            total_projects=model.total_projects or 0,
            active_projects=model.active_projects or 0,
            total_invoiced=model.total_invoiced or 0.0,
            total_paid=model.total_paid or 0.0,
            outstanding_balance=model.outstanding_balance or 0.0
        )
        
        # Set entity metadata
        client.id = model.id
        client.created_at = model.created_at
        client.updated_at = model.updated_at
        client.version = model.version or 1
        
        return client