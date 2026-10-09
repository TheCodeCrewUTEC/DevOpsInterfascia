package uy.interfascia.keycloak;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.Map;

import org.jboss.logging.Logger;
import org.keycloak.events.Event;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventType;
import org.keycloak.events.admin.AdminEvent;
import org.keycloak.models.AbstractKeycloakTransaction;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.RoleModel;
import org.keycloak.models.UserModel;

/**
 * Tras el registro: deja la cuenta deshabilitada (pendiente de aprobación),
 * marca el atributo estadoAprobacion, asigna el rol de realm según el perfil elegido
 * y avisa a la API para que guarde el usuario en la base de la app.
 */
public class RegistrationApprovalListenerProvider implements EventListenerProvider {

    public static final String PROVIDER_ID = "registration-approval";
    public static final String ATTR_ESTADO = "estadoAprobacion";
    public static final String ESTADO_PENDIENTE = "pendiente";

    private static final Logger LOG = Logger.getLogger(RegistrationApprovalListenerProvider.class);

    // Sin "Administrador": el rol admin nunca se obtiene registrándose, se asigna a mano
    private static final Map<String, String> ROL_POR_PERFIL = Map.of(
            "Gestor/a de innovación", "gestor_innovacion",
            "Investigador/a", "investigador",
            "Emprendedor/a / Empresario/a", "emprendedor",
            "Otros", "emprendedor"
    );

    // La API por la red de Docker y el secreto compartido con /internal/usuarios
    private static final String API_URL = System.getenv("INTERFASCIA_API_URL");
    private static final String INTERNAL_SECRET = System.getenv("INTERNAL_API_SECRET");

    // HTTP/1.1: con el upgrade a h2c que intenta Java por defecto, uvicorn descarta el body (422)
    private static final HttpClient HTTP = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(Duration.ofSeconds(3))
            .build();

    private final KeycloakSession session;

    public RegistrationApprovalListenerProvider(KeycloakSession session) {
        this.session = session;
    }

    @Override
    public void onEvent(Event event) {
        if (event.getType() != EventType.REGISTER) {
            return;
        }

        RealmModel realm = session.realms().getRealm(event.getRealmId());
        if (realm == null || event.getUserId() == null) {
            return;
        }

        UserModel user = session.users().getUserById(realm, event.getUserId());
        if (user == null) {
            return;
        }

        user.setEnabled(false);
        user.setSingleAttribute(ATTR_ESTADO, ESTADO_PENDIENTE);
        asignarRolDesdePerfil(realm, user);
        avisarRegistroDespuesDelCommit(user.getId());

        LOG.infof(
                "Usuario %s registrado: cuenta pendiente de aprobación del administrador.",
                user.getUsername()
        );
    }

    private void asignarRolDesdePerfil(RealmModel realm, UserModel user) {
        List<String> perfiles = user.getAttributes().getOrDefault("perfil", List.of());
        if (perfiles.isEmpty()) {
            return;
        }

        String perfil = perfiles.get(0);
        String nombreRol = ROL_POR_PERFIL.get(perfil);
        if (nombreRol == null) {
            LOG.warnf("Perfil de registro desconocido: %s", perfil);
            return;
        }

        RoleModel rol = realm.getRole(nombreRol);
        if (rol == null) {
            LOG.warnf("No existe el rol de realm '%s' para el perfil '%s'.", nombreRol, perfil);
            return;
        }

        if (!user.hasRole(rol)) {
            user.grantRole(rol);
        }
    }

    /**
     * El aviso sale recién cuando Keycloak confirma la transacción: la API lee el
     * usuario por la API de administración y antes del commit todavía no existe.
     * Si la API no responde, el registro sigue igual y el admin puede sincronizar.
     */
    private void avisarRegistroDespuesDelCommit(String userId) {
        if (API_URL == null || API_URL.isBlank() || INTERNAL_SECRET == null || INTERNAL_SECRET.isBlank()) {
            LOG.warn("Falta INTERFASCIA_API_URL o INTERNAL_API_SECRET: el registro no se avisa a la API.");
            return;
        }

        session.getTransactionManager().enlistAfterCompletion(new AbstractKeycloakTransaction() {
            @Override
            protected void commitImpl() {
                avisarRegistro(userId);
            }

            @Override
            protected void rollbackImpl() {
                // El registro no se guardó: no hay nada que avisar
            }
        });
    }

    private void avisarRegistro(String userId) {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(API_URL.replaceAll("/+$", "") + "/internal/usuarios"))
                .timeout(Duration.ofSeconds(15))
                .header("Content-Type", "application/json")
                .header("X-Internal-Secret", INTERNAL_SECRET)
                .POST(HttpRequest.BodyPublishers.ofString("{\"keycloak_id\":\"" + userId + "\"}"))
                .build();

        // Asíncrono: el usuario no espera a la API para terminar el registro
        HTTP.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .whenComplete((response, error) -> {
                    if (error != null) {
                        LOG.warnf("No se pudo avisar el registro %s a la API: %s", userId, error.getMessage());
                    } else if (response.statusCode() >= 300) {
                        LOG.warnf("La API rechazó el aviso de registro %s (%d): %s",
                                userId, response.statusCode(), response.body());
                    }
                });
    }

    @Override
    public void onEvent(AdminEvent event, boolean includeRepresentation) {
        // No aplica a eventos de administración.
    }

    @Override
    public void close() {
    }
}
