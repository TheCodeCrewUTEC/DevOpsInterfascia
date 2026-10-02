package uy.interfascia.keycloak;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import jakarta.ws.rs.core.MultivaluedMap;

import org.jboss.logging.Logger;
import org.keycloak.authentication.AuthenticationFlowContext;
import org.keycloak.authentication.AuthenticationFlowError;
import org.keycloak.authentication.Authenticator;
import org.keycloak.common.util.SecretGenerator;
import org.keycloak.common.util.Time;
import org.keycloak.email.EmailException;
import org.keycloak.email.EmailTemplateProvider;
import org.keycloak.forms.login.LoginFormsProvider;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserModel;
import org.keycloak.sessions.AuthenticationSessionModel;

/**
 * Segundo factor: después del usuario y contraseña manda un código de 6 dígitos al correo
 * del usuario y muestra email-code.ftl para ingresarlo.
 * El código vive en la sesión de autenticación (no en la base), así que vence solo si el
 * usuario abandona el login.
 */
public class EmailOtpAuthenticator implements Authenticator {

    private static final Logger LOG = Logger.getLogger(EmailOtpAuthenticator.class);

    private static final int DIGITOS = 6;
    private static final int VALIDEZ_SEGUNDOS = 5 * 60;
    private static final int MAX_INTENTOS = 5;
    private static final int MAX_ENVIOS = 3;
    private static final int ESPERA_REENVIO_SEGUNDOS = 30;

    private static final String NOTA_CODIGO = "email-otp-codigo";
    private static final String NOTA_VENCE = "email-otp-vence";
    private static final String NOTA_INTENTOS = "email-otp-intentos";
    private static final String NOTA_ENVIOS = "email-otp-envios";
    private static final String NOTA_ULTIMO_ENVIO = "email-otp-ultimo-envio";

    private static final String FORMULARIO = "email-code.ftl";

    @Override
    public void authenticate(AuthenticationFlowContext context) {
        if (context.getUser().getEmail() == null) {
            // Sin correo no hay a dónde mandar el código: cortamos en vez de dejar pasar sin 2FA
            context.failure(AuthenticationFlowError.INVALID_USER);
            return;
        }

        if (!enviarCodigo(context)) {
            context.failureChallenge(AuthenticationFlowError.INTERNAL_ERROR,
                    formulario(context).setError("emailCodeSendError").createForm(FORMULARIO));
            return;
        }

        context.challenge(formulario(context).createForm(FORMULARIO));
    }

    @Override
    public void action(AuthenticationFlowContext context) {
        MultivaluedMap<String, String> datos = context.getHttpRequest().getDecodedFormParameters();
        AuthenticationSessionModel sesion = context.getAuthenticationSession();

        if (datos.containsKey("resend")) {
            reenviar(context);
            return;
        }

        String esperado = sesion.getAuthNote(NOTA_CODIGO);
        if (esperado == null) {
            // Se agotaron los intentos de este código: solo queda pedir otro
            context.failureChallenge(AuthenticationFlowError.INVALID_CREDENTIALS,
                    formulario(context).setError("emailCodeTooManyAttempts").createForm(FORMULARIO));
            return;
        }

        if (Time.currentTime() > Integer.parseInt(sesion.getAuthNote(NOTA_VENCE))) {
            borrarCodigo(sesion);
            context.failureChallenge(AuthenticationFlowError.EXPIRED_CODE,
                    formulario(context).setError("emailCodeExpired").createForm(FORMULARIO));
            return;
        }

        String ingresado = datos.getFirst("code");
        ingresado = ingresado == null ? "" : ingresado.replaceAll("\\s", "");

        if (MessageDigest.isEqual(esperado.getBytes(StandardCharsets.UTF_8), ingresado.getBytes(StandardCharsets.UTF_8))) {
            borrarCodigo(sesion);
            sesion.removeAuthNote(NOTA_ENVIOS);
            sesion.removeAuthNote(NOTA_ULTIMO_ENVIO);
            context.success();
            return;
        }

        int intentos = entero(sesion.getAuthNote(NOTA_INTENTOS)) + 1;
        sesion.setAuthNote(NOTA_INTENTOS, String.valueOf(intentos));
        context.getEvent().user(context.getUser()).error("invalid_email_otp");

        String error = "emailCodeInvalid";
        if (intentos >= MAX_INTENTOS) {
            borrarCodigo(sesion);
            error = "emailCodeTooManyAttempts";
        }
        context.failureChallenge(AuthenticationFlowError.INVALID_CREDENTIALS,
                formulario(context).setError(error).createForm(FORMULARIO));
    }

    private void reenviar(AuthenticationFlowContext context) {
        AuthenticationSessionModel sesion = context.getAuthenticationSession();
        int desdeUltimo = Time.currentTime() - entero(sesion.getAuthNote(NOTA_ULTIMO_ENVIO));

        LoginFormsProvider form = formulario(context);
        if (entero(sesion.getAuthNote(NOTA_ENVIOS)) >= MAX_ENVIOS) {
            form.setError("emailCodeTooManyResends");
        } else if (desdeUltimo < ESPERA_REENVIO_SEGUNDOS) {
            form.setError("emailCodeResendWait", String.valueOf(ESPERA_REENVIO_SEGUNDOS - desdeUltimo));
        } else if (enviarCodigo(context)) {
            form.setInfo("emailCodeResent");
        } else {
            form.setError("emailCodeSendError");
        }
        context.challenge(form.createForm(FORMULARIO));
    }

    /** Genera un código nuevo (reemplaza al anterior) y lo manda. Devuelve false si falló el envío. */
    private boolean enviarCodigo(AuthenticationFlowContext context) {
        KeycloakSession session = context.getSession();
        RealmModel realm = context.getRealm();
        UserModel user = context.getUser();
        AuthenticationSessionModel sesion = context.getAuthenticationSession();

        String codigo = SecretGenerator.getInstance().randomString(DIGITOS, SecretGenerator.DIGITS);

        Map<String, Object> atributos = new HashMap<>();
        atributos.put("code", codigo);
        atributos.put("ttlMinutes", VALIDEZ_SEGUNDOS / 60);

        try {
            session.getProvider(EmailTemplateProvider.class)
                    .setRealm(realm)
                    .setUser(user)
                    .setAuthenticationSession(sesion)
                    .send("emailCodeSubject", List.of(), FORMULARIO, atributos);
        } catch (EmailException e) {
            LOG.errorf(e, "No se pudo enviar el código por correo al usuario %s", user.getUsername());
            return false;
        }

        sesion.setAuthNote(NOTA_CODIGO, codigo);
        sesion.setAuthNote(NOTA_VENCE, String.valueOf(Time.currentTime() + VALIDEZ_SEGUNDOS));
        sesion.setAuthNote(NOTA_INTENTOS, "0");
        sesion.setAuthNote(NOTA_ENVIOS, String.valueOf(entero(sesion.getAuthNote(NOTA_ENVIOS)) + 1));
        sesion.setAuthNote(NOTA_ULTIMO_ENVIO, String.valueOf(Time.currentTime()));
        return true;
    }

    private LoginFormsProvider formulario(AuthenticationFlowContext context) {
        return context.form().setAttribute("emailEnmascarado", enmascarar(context.getUser().getEmail()));
    }

    private static void borrarCodigo(AuthenticationSessionModel sesion) {
        sesion.removeAuthNote(NOTA_CODIGO);
        sesion.removeAuthNote(NOTA_VENCE);
        sesion.removeAuthNote(NOTA_INTENTOS);
    }

    /** antonio@gmail.com -> an*****@gmail.com */
    static String enmascarar(String email) {
        int arroba = email.indexOf('@');
        if (arroba <= 0) {
            return email;
        }
        int visibles = Math.min(2, arroba);
        return email.substring(0, visibles) + "*".repeat(Math.max(arroba - visibles, 3)) + email.substring(arroba);
    }

    private static int entero(String valor) {
        try {
            return valor == null ? 0 : Integer.parseInt(valor);
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    @Override
    public boolean requiresUser() {
        return true;
    }

    @Override
    public boolean configuredFor(KeycloakSession session, RealmModel realm, UserModel user) {
        // Siempre "configurado": el caso sin correo lo corta authenticate()
        return true;
    }

    @Override
    public void setRequiredActions(KeycloakSession session, RealmModel realm, UserModel user) {
    }

    @Override
    public void close() {
    }
}
