from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Schemi Pydantic per l'autenticazione
#
# Gli schemi definiscono la forma dei dati che entrano ed escono dagli endpoint.
# Pydantic valida automaticamente ogni richiesta: se il client manda dati
# nel formato sbagliato, FastAPI risponde con un errore 422 dettagliato
# ancora prima che il nostro codice venga eseguito.
# ---------------------------------------------------------------------------

# Dati che il client manda al momento del login
class LoginRequest(BaseModel):
    username: str = Field(..., example="admin")
    password: str = Field(..., example="admin123")

# Dati che il server restituisce dopo un login riuscito
class TokenResponse(BaseModel):
    access_token: str          # Il token da usare nelle chiamate successive
    token_type: str = "bearer" # Sempre "bearer" per il nostro sistema
    username: str              # Utile al frontend per mostrare "Benvenuto, admin"

# Dati per invitare un nuovo operatore (solo l'Amministratore Supremo può farlo)
class RegisterRequest(BaseModel):
    username: str = Field(..., example="funzionario")
    email: str = Field(..., example="funzionario@comune.it")

# Dati per avviare il reset password: basta lo username, senza autenticazione.
# Il backend manderà un'email con il link di reset (se l'utente esiste).
class ForgotPasswordRequest(BaseModel):
    username: str = Field(..., example="admin")

# Dati per completare il reset: il token ricevuto via email + la nuova password
class ConfirmResetPasswordRequest(BaseModel):
    token: str = Field(...)
    password: str = Field(..., description="Nuova password da impostare")

    @field_validator('password')
    def validate_password_strength(cls, v):
        from zxcvbn import zxcvbn
        result = zxcvbn(v)
        if result['score'] < 3:
            raise ValueError("La password è troppo debole. Usa una password più complessa.")
        return v

# Dati per cambiare la propria password da loggati:
# serve la password attuale come verifica di identità aggiuntiva
class ChangeOwnPasswordRequest(BaseModel):
    current_password: str = Field(...)
    new_password: str = Field(..., description="Nuova password da impostare")

    @field_validator('new_password')
    def validate_new_password_strength(cls, v):
        from zxcvbn import zxcvbn
        result = zxcvbn(v)
        if result['score'] < 3:
            raise ValueError("La nuova password è troppo debole. Usa una password più complessa.")
        return v

from typing import Optional

# Dati restituiti quando l'admin supremo richiede la lista utenti
class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    
    class Config:
        from_attributes = True
