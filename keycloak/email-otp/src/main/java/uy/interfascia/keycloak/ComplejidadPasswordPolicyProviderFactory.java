package uy.interfascia.keycloak;

import org.keycloak.Config;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.policy.PasswordPolicyProvider;
import org.keycloak.policy.PasswordPolicyProviderFactory;

public class ComplejidadPasswordPolicyProviderFactory implements PasswordPolicyProviderFactory {

    // Es el nombre que se usa en la passwordPolicy del realm: complejidad(3)
    public static final String ID = "complejidad";
    public static final int DEFAULT_VALUE = 3;

    @Override
    public PasswordPolicyProvider create(KeycloakSession session) {
        return new ComplejidadPasswordPolicyProvider(session);
    }

    @Override
    public String getId() {
        return ID;
    }

    @Override
    public String getDisplayName() {
        return "Complejidad: N de 4 categorías (Interfascia)";
    }

    @Override
    public String getConfigType() {
        return PasswordPolicyProvider.INT_CONFIG_TYPE;
    }

    @Override
    public String getDefaultConfigValue() {
        return String.valueOf(DEFAULT_VALUE);
    }

    @Override
    public boolean isMultiplSupported() {
        return false;
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
