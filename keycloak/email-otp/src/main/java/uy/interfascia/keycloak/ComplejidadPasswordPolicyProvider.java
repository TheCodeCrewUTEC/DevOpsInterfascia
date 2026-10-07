package uy.interfascia.keycloak;

import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserModel;
import org.keycloak.policy.PasswordPolicyProvider;
import org.keycloak.policy.PolicyError;

// Pide un mínimo de categorías distintas (por defecto 3 de 4): mayúscula, minúscula, número y
// carácter especial. Como en specialChars de Keycloak, "especial" es todo lo que no es letra ni número.
public class ComplejidadPasswordPolicyProvider implements PasswordPolicyProvider {

    static final String ERROR_MESSAGE = "invalidPasswordComplejidadMessage";

    private final KeycloakSession session;

    public ComplejidadPasswordPolicyProvider(KeycloakSession session) {
        this.session = session;
    }

    @Override
    public PolicyError validate(RealmModel realm, UserModel user, String password) {
        return validar(realm, password);
    }

    @Override
    public PolicyError validate(String user, String password) {
        return validar(session.getContext().getRealm(), password);
    }

    private PolicyError validar(RealmModel realm, String password) {
        int minimo = realm.getPasswordPolicy().getPolicyConfig(ComplejidadPasswordPolicyProviderFactory.ID);
        return categorias(password) < minimo ? new PolicyError(ERROR_MESSAGE, minimo) : null;
    }

    static int categorias(String password) {
        boolean mayuscula = false, minuscula = false, numero = false, especial = false;
        for (int i = 0; i < password.length(); ) {
            int c = password.codePointAt(i);
            if (Character.isUpperCase(c)) {
                mayuscula = true;
            } else if (Character.isLowerCase(c)) {
                minuscula = true;
            } else if (Character.isDigit(c)) {
                numero = true;
            } else if (!Character.isLetterOrDigit(c)) {
                especial = true;
            }
            i += Character.charCount(c);
        }
        return (mayuscula ? 1 : 0) + (minuscula ? 1 : 0) + (numero ? 1 : 0) + (especial ? 1 : 0);
    }

    @Override
    public Object parseConfig(String value) {
        int minimo = parseInteger(value, ComplejidadPasswordPolicyProviderFactory.DEFAULT_VALUE);
        if (minimo < 1 || minimo > 4) {
            throw new IllegalArgumentException("complejidad debe estar entre 1 y 4");
        }
        return minimo;
    }

    @Override
    public void close() {
    }
}
