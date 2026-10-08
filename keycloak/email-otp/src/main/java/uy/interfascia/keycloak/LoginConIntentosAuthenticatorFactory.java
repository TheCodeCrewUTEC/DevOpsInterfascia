package uy.interfascia.keycloak;

import org.keycloak.authentication.Authenticator;
import org.keycloak.authentication.authenticators.browser.UsernamePasswordFormFactory;
import org.keycloak.models.KeycloakSession;

// Igual que "Username Password Form" de Keycloak, con contador de intentos y aviso de bloqueo
public class LoginConIntentosAuthenticatorFactory extends UsernamePasswordFormFactory {

    // Es el "provider" que se usa en el flujo del realm (realm-interfascia.json y configurar-email-otp.sh)
    public static final String ID = "auth-username-password-form-intentos";

    @Override
    public String getId() {
        return ID;
    }

    @Override
    public String getDisplayType() {
        return "Usuario y contraseña con contador de intentos (Interfascia)";
    }

    @Override
    public String getHelpText() {
        return "Valida usuario y contraseña, avisa cuántos intentos quedan y cuánto falta cuando la cuenta está bloqueada.";
    }

    @Override
    public Authenticator create(KeycloakSession session) {
        return new LoginConIntentosAuthenticator(session);
    }
}
