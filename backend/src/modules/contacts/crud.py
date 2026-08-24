from fastcrud import FastCRUD

from .models import Contact

crud_contacts: FastCRUD = FastCRUD(Contact)
