from fastcrud import FastCRUD

from .models import Company

crud_companies: FastCRUD = FastCRUD(Company)
