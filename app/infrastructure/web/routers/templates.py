"""
Templates and PDF management router.
Handles template customization, company profiles, and PDF generation.
"""

from typing import Annotated, List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse

from app.infrastructure.auth import get_current_user_id
from app.infrastructure.pdf.template_manager import (
    template_manager,
    CompanyProfile,
    TemplateSettings,
    TemplateTheme
)
from app.infrastructure.storage.storage_service import get_storage_service
from app.application.use_cases.generate_pdf_use_case import (
    GenerateReportPDFUseCase,
    GenerateReportPDFRequest
)
from app.infrastructure.db.database import get_db_session
from app.infrastructure.repositories.time_entry_repository import SQLAlchemyTimeEntryRepository
from app.infrastructure.repositories.project_repository import SQLAlchemyProjectRepository
from app.infrastructure.repositories.client_repository import SQLAlchemyClientRepository
from app.domain.models.base import ValidationError
from pydantic import BaseModel


router = APIRouter()


# Request/Response Models
class CompanyProfileRequest(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    tax_id_label: str = "Tax ID"
    footer_text: Optional[str] = None
    primary_color: str = "#2c3e50"
    secondary_color: str = "#34495e"
    accent_color: str = "#3498db"


class TemplateSettingsRequest(BaseModel):
    theme: str = "professional"
    font_family: str = "Helvetica"
    font_size: int = 11
    show_logo: bool = True
    show_company_details: bool = True
    show_tax_info: bool = True
    include_payment_terms: bool = True
    include_notes_section: bool = True
    currency_position: str = "before"
    date_format: str = "%d/%m/%Y"
    number_format: str = "INV-{:04d}"
    custom_css: Optional[str] = None


@router.get("/themes")
async def list_template_themes():
    """
    List all available template themes.
    """
    themes = template_manager.list_available_themes()
    return {"themes": themes}


@router.get("/company-profile")
async def get_company_profile(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Get current user's company profile.
    """
    try:
        profile = template_manager.get_company_profile(user_id)
        return profile.__dict__
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get company profile: {str(e)}"
        )


@router.put("/company-profile")
async def update_company_profile(
    request: CompanyProfileRequest,
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Update current user's company profile.
    """
    try:
        profile = CompanyProfile(**request.dict())
        template_manager.save_company_profile(user_id, profile)
        return {"message": "Company profile updated successfully", "profile": profile.__dict__}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update company profile: {str(e)}"
        )


@router.get("/settings")
async def get_template_settings(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Get current user's template settings.
    """
    try:
        settings = template_manager.get_template_settings(user_id)
        settings_dict = settings.__dict__.copy()
        settings_dict["theme"] = settings.theme.value
        return settings_dict
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template settings: {str(e)}"
        )


@router.put("/settings")
async def update_template_settings(
    request: TemplateSettingsRequest,
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Update current user's template settings.
    """
    try:
        # Validate theme
        if request.theme not in [t.value for t in TemplateTheme]:
            raise ValueError(f"Invalid theme: {request.theme}")
        
        settings_dict = request.dict()
        settings_dict["theme"] = TemplateTheme(request.theme)
        settings = TemplateSettings(**settings_dict)
        
        template_manager.save_template_settings(user_id, settings)
        
        response_dict = settings.__dict__.copy()
        response_dict["theme"] = settings.theme.value
        
        return {"message": "Template settings updated successfully", "settings": response_dict}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update template settings: {str(e)}"
        )


@router.post("/company-logo")
async def upload_company_logo(
    file: UploadFile = File(...),
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Upload company logo image.
    
    - **file**: Logo image file (JPEG, PNG, GIF, WebP, SVG)
    """
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        # Read file content
        content = await file.read()
        
        # Upload to storage
        storage_service = get_storage_service()
        result = await storage_service.upload_company_logo(
            image_content=content,
            filename=file.filename,
            user_id=user_id,
            content_type=file.content_type
        )
        
        # Update company profile with logo URL
        profile = template_manager.get_company_profile(user_id)
        profile.logo_url = result["public_url"]
        template_manager.save_company_profile(user_id, profile)
        
        return {
            "message": "Logo uploaded successfully",
            "logo_url": result["public_url"],
            "file_info": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload logo: {str(e)}"
        )


@router.get("/preview/{theme}")
async def preview_template(
    theme: str,
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Generate a preview of a template theme.
    
    - **theme**: Template theme name
    """
    try:
        # Validate theme
        if theme not in [t.value for t in TemplateTheme]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid theme: {theme}"
            )
        
        theme_enum = TemplateTheme(theme)
        preview_data = template_manager.create_template_preview_data(theme_enum)
        
        # Add user's company profile
        company_profile = template_manager.get_company_profile(user_id)
        preview_data["company"] = company_profile.__dict__
        
        from app.infrastructure.pdf.pdf_service import pdf_service
        
        # Generate preview PDF
        template_file = template_manager.get_template_file(theme_enum)
        pdf_path = pdf_service.generate_invoice_pdf(
            invoice=type('obj', (object,), preview_data["invoice"]),
            client=type('obj', (object,), preview_data["client"]),
            project=type('obj', (object,), preview_data.get("project", {})),
            company_data=preview_data["company"],
            template_name=template_file
        )
        
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"preview_{theme}.pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}"
        )


@router.post("/generate-report")
async def generate_report_pdf(
    report_type: str = Query(..., description="Report type (time_summary, financial, project_summary)"),
    user_id: Annotated[str, Depends(get_current_user_id)],
    project_id: Optional[int] = Query(None, description="Project ID for project reports"),
    client_id: Optional[int] = Query(None, description="Client ID for client reports"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    template: str = Query("professional", description="Template theme"),
    include_charts: bool = Query(True, description="Include charts in report")
):
    """
    Generate a report PDF.
    
    - **report_type**: Type of report (time_summary, financial, project_summary)
    - **project_id**: Optional project filter
    - **client_id**: Optional client filter  
    - **start_date**: Optional start date filter
    - **end_date**: Optional end date filter
    - **template**: Template theme to use
    - **include_charts**: Whether to include charts
    """
    try:
        from datetime import datetime
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        # Get repositories
        session = next(get_db_session())
        time_entry_repo = SQLAlchemyTimeEntryRepository(session)
        project_repo = SQLAlchemyProjectRepository(session)
        client_repo = SQLAlchemyClientRepository(session)
        
        # Create use case
        use_case = GenerateReportPDFUseCase(
            time_entry_repository=time_entry_repo,
            project_repository=project_repo,
            client_repository=client_repo
        )
        
        # Create request
        request = GenerateReportPDFRequest(
            report_type=report_type,
            project_id=project_id,
            client_id=client_id,
            start_date=start_dt,
            end_date=end_dt,
            template_theme=template,
            include_charts=include_charts
        )
        
        # Generate report
        result = await use_case.execute(user_id, request)
        
        return FileResponse(
            path=result.file_path,
            media_type="application/pdf",
            filename=result.filename,
            headers={"Content-Disposition": f"attachment; filename={result.filename}"}
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.get("/export-config")
async def export_template_config(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Export complete template configuration.
    """
    try:
        config = template_manager.export_template_config(user_id)
        return config
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export config: {str(e)}"
        )


@router.post("/import-config")
async def import_template_config(
    config: Dict[str, Any],
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Import template configuration.
    
    - **config**: Configuration object to import
    """
    try:
        template_manager.import_template_config(user_id, config)
        return {"message": "Configuration imported successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to import config: {str(e)}"
        )


@router.get("/custom-css")
async def get_custom_css(
    user_id: Annotated[str, Depends(get_current_user_id)]
):
    """
    Get generated custom CSS for current user settings.
    """
    try:
        settings = template_manager.get_template_settings(user_id)
        profile = template_manager.get_company_profile(user_id)
        
        custom_css = template_manager.generate_custom_css(settings, profile)
        
        return JSONResponse(
            content={"css": custom_css},
            media_type="application/json"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate CSS: {str(e)}"
        )