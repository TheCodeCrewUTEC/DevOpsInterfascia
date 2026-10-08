package uy.interfascia.keycloak;

import java.util.List;

import org.keycloak.authentication.AuthenticationFlowContext;
import org.keycloak.authentication.AuthenticationFlowError;
import org.keycloak.authentication.authenticators.browser.UsernamePasswordForm;
import org.keycloak.authentication.authenticators.util.AuthenticatorUtils;
import org.keycloak.common.util.Time;
import org.keycloak.events.Errors;
import org.keycloak.forms.login.LoginFormsProvider;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserLoginFailureModel;
import org.keycloak.models.UserModel;
import org.keycloak.models.utils.FormMessage;
import org.keycloak.representations.idm.CredentialRepresentation;

import static org.keycloak.services.validation.Validation.FIELD_PASSWORD;
import static org.keycloak.services.validation.Validation.FIELD_USERNAME;

import jakarta.ws.rs.core.MultivaluedMap;
import jakarta.ws.rs.core.Response;

/**
 * Formulario de usuario y contraseña de Keycloak que además avisa cuántos intentos quedan
 * antes del bloqueo por fuerza bruta, y cuántos minutos faltan cuando la cuenta ya está bloqueada.
 *
 * El bloqueo lo sigue haciendo Keycloak (bruteForceProtected, failureFactor, waitIncrementSeconds
 * del realm); acá solo se calculan los mensajes. Keycloak suma la falla nueva en segundo plano,
 * después de armar la respuesta, por eso se cuentan las fallas anteriores más esta.
 */
public class LoginConIntentosAuthenticator extends UsernamePasswordForm {

    // Atributos que lee login.ftl para el contador y el aviso de bloqueo
    static final String ATRIBUTO_RESTANTES = "intentosRestantes";
    static final String ATRIBUTO_PERMITIDOS = "intentosPermitidos";
    static final String ATRIBUTO_BLOQUEO = "bloqueoMinutos";

    public LoginConIntentosAuthenticator(KeycloakSession session) {
        super(session);
    }

    @Override
    public boolean validatePassword(AuthenticationFlowContext context, UserModel user,
                                    MultivaluedMap<String, String> inputData, boolean clearUser) {
        RealmModel realm = context.getRealm();
        String password = inputData.getFirst(CredentialRepresentation.PASSWORD);

        if (!realm.isBruteForceProtected() || password == null || password.isEmpty()) {
            return super.validatePassword(context, user, inputData, clearUser);
        }

        // Se lee antes de validar: después Keycloak ya sumó (o no) la falla de este intento
        String errorBloqueo = AuthenticatorUtils.getDisabledByBruteForceEventError(context, user);
        UserLoginFailureModel fallas = context.getSession().loginFailures().getUserLoginFailure(realm, user.getId());
        long ahora = Time.currentTimeMillis();
        int previas = fallasVigentes(realm, fallas, ahora);

        if (super.validatePassword(context, user, inputData, clearUser)) {
            return true;
        }

        if (errorBloqueo != null) {
            // Bloqueo permanente: se deja el mensaje de Keycloak
            if (Errors.USER_TEMPORARILY_DISABLED.equals(errorBloqueo) && fallas != null) {
                long segundos = fallas.getFailedLoginNotBefore() - ahora / 1000;
                context.forceChallenge(avisoBloqueo(context, Math.max(1, (segundos + 59) / 60)));
            }
            return false;
        }

        int restantes = realm.getFailureFactor() - (previas + 1);
        Response respuesta = restantes > 0
                ? avisoIntentos(context, restantes)
                : avisoBloqueo(context, minutosDeBloqueo(realm));
        context.failureChallenge(AuthenticationFlowError.INVALID_CREDENTIALS, respuesta);
        return false;
    }

    // Mismo criterio que DefaultBruteForceProtector: si la última falla es muy vieja, se empieza de cero
    private static int fallasVigentes(RealmModel realm, UserLoginFailureModel fallas, long ahora) {
        if (fallas == null) {
            return 0;
        }
        long ultima = fallas.getLastFailure();
        if (ultima > 0 && ahora - ultima > realm.getMaxDeltaTimeSeconds() * 1000L) {
            return 0;
        }
        return fallas.getNumFailures();
    }

    private static long minutosDeBloqueo(RealmModel realm) {
        long segundos = Math.min(realm.getWaitIncrementSeconds(), realm.getMaxFailureWaitSeconds());
        return Math.max(1, (segundos + 59) / 60);
    }

    private Response avisoIntentos(AuthenticationFlowContext context, int restantes) {
        String clave = restantes == 1 ? "contrasenaIncorrectaUltimoIntento" : "contrasenaIncorrectaIntentos";
        LoginFormsProvider form = formulario(context)
                .setAttribute(ATRIBUTO_RESTANTES, restantes)
                .setAttribute(ATRIBUTO_PERMITIDOS, context.getRealm().getFailureFactor())
                .setErrors(List.of(new FormMessage(FIELD_PASSWORD, clave, restantes, minutosDeBloqueo(context.getRealm()))));
        return createLoginForm(form);
    }

    private Response avisoBloqueo(AuthenticationFlowContext context, long minutos) {
        LoginFormsProvider form = formulario(context)
                .setAttribute(ATRIBUTO_BLOQUEO, minutos)
                .setErrors(List.of(new FormMessage(campoUsuario(context), "usuarioBloqueadoIntentos", minutos)));
        return createLoginForm(form);
    }

    // Como Keycloak: si el usuario no se muestra (reautenticación), el error va en la contraseña
    private static String campoUsuario(AuthenticationFlowContext context) {
        boolean oculto = Boolean.parseBoolean(context.getAuthenticationSession().getAuthNote(USERNAME_HIDDEN));
        return oculto ? FIELD_PASSWORD : FIELD_USERNAME;
    }

    // setErrors reemplaza el "Usuario o contraseña incorrectos" que ya agregó Keycloak al mismo formulario
    private static LoginFormsProvider formulario(AuthenticationFlowContext context) {
        return context.form().setExecution(context.getExecution().getId());
    }
}
