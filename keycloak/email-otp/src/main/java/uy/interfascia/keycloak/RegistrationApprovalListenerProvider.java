package uy.interfascia.keycloak;

import java.util.List;
import java.util.Map;

import org.jboss.logging.Logger;
import org.keycloak.events.Event;
import org.keycloak.events.EventListenerProvider;
import org.keycloak.events.EventType;
import org.keycloak.events.admin.AdminEvent;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.RoleModel;
import org.keycloak.models.UserModel;

/**
 * Tras el registro: deja la cuenta deshabilitada (pendiente de aprobación),
 * marca el atributo estadoAprobacion y asigna el rol de realm según el perfil elegido.
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

    @Override
    public void onEvent(AdminEvent event, boolean includeRepresentation) {
        // No aplica a eventos de administración.
    }

    @Override
    public void close() {
    }
}
