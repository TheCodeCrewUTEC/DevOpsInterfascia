package uy.interfascia.keycloak;

import java.util.List;

import org.keycloak.Config;
import org.keycloak.authentication.Authenticator;
import org.keycloak.authentication.AuthenticatorFactory;
import org.keycloak.models.AuthenticationExecutionModel.Requirement;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.provider.ProviderConfigProperty;

public class EmailOtpAuthenticatorFactory implements AuthenticatorFactory {

    // Es el "provider" que se usa en el flujo del realm (realm-interfascia.json y configurar-email-otp.sh)
    public static final String ID = "email-otp";

    private static final EmailOtpAuthenticator INSTANCIA = new EmailOtpAuthenticator();

    @Override
    public String getId() {
        return ID;
    }

    @Override
    public String getDisplayType() {
        return "Código por correo (Interfascia)";
    }

    @Override
    public String getHelpText() {
        return "Envía un código de 6 dígitos al correo del usuario y lo pide antes de terminar el inicio de sesión.";
    }

    @Override
    public String getReferenceCategory() {
        return "email-otp";
    }

    @Override
    public Requirement[] getRequirementChoices() {
        return new Requirement[] { Requirement.REQUIRED, Requirement.ALTERNATIVE, Requirement.DISABLED };
    }

    @Override
    public boolean isConfigurable() {
        return false;
    }

    @Override
    public boolean isUserSetupAllowed() {
        return false;
    }

    @Override
    public List<ProviderConfigProperty> getConfigProperties() {
        return List.of();
    }

    @Override
    public Authenticator create(KeycloakSession session) {
        return INSTANCIA;
    }

    @Override
    public void init(Config.Scope config) {
    }

    @Override
    public void postInit(KeycloakSessionFactory factory) {
    }

    @Override
    public void close() {
    }
}
