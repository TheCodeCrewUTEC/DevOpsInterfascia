<#--
  Plantilla base del tema Interfascia.
  Replica el navbar y el footer de la app Next.js para que el login no parezca otro sitio.
  variant="card"  -> tarjeta blanca centrada sobre fondo oscuro (login, recuperar contraseña, errores...)
  variant="page"  -> página completa en dos columnas (registro)
-->
<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false variant="card">
<#assign appUrl = (properties.appUrl!"http://localhost:3000")?remove_ending("/")>
<!DOCTYPE html>
<html lang="${lang}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex, nofollow">
    <title>${msg("loginTitle",(realm.displayName!''))}</title>
    <link rel="icon" href="${appUrl}/favicon.ico" />
    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
            <link href="${url.resourcesPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <#if scripts??>
        <#list scripts as script>
            <script src="${script}" type="text/javascript"></script>
        </#list>
    </#if>
    <script type="module">
        import { startSessionPolling } from "${url.resourcesPath}/js/authChecker.js";
        startSessionPolling("${url.ssoLoginInOtherTabsUrl?no_esc}");
    </script>
    <#if authenticationSession??>
        <script type="module">
            import { checkAuthSession } from "${url.resourcesPath}/js/authChecker.js";
            checkAuthSession("${authenticationSession.authSessionIdHash}");
        </script>
    </#if>
</head>

<body class="ifx-body ${bodyClass}" data-page-id="login-${pageId}">

    <nav class="ifx-navbar">
        <div class="ifx-navbar__brand">
            <div class="ifx-navbar__logo">Logo</div>
            <a href="${appUrl}/">Interfascia</a>
        </div>

        <div class="ifx-navbar__links">
            <a href="${appUrl}/repositorio">Repositorio</a>
            <a href="${appUrl}/#que-es-interfascia">¿Qué es Interfascia?</a>
            <a href="${appUrl}/consultor-ia">Consultor IA</a>
            <a href="${appUrl}/analisis-datos">Análisis de Datos</a>
        </div>

        <div class="ifx-navbar__actions">
            <a class="ifx-btn ifx-btn--primary" href="${(url.loginUrl)!(appUrl + '/login')}">Iniciar sesión</a>
            <#if realm.registrationAllowed>
                <a class="ifx-btn ifx-btn--secondary" href="${(url.registrationUrl)!(appUrl + '/registro')}">Registrate</a>
            </#if>
        </div>
    </nav>

    <#if variant == "page">
        <main class="ifx-page">
            <#nested "form">
        </main>
    <#else>
        <main class="ifx-overlay">
            <div class="ifx-card">
                <a href="${appUrl}/" class="ifx-card__close" aria-label="Cerrar">&times;</a>

                <#if !(auth?has_content && auth.showUsername() && !auth.showResetCredentials())>
                    <h1 class="ifx-card__title"><#nested "header"></h1>
                <#else>
                    <h1 class="ifx-card__title"><#nested "header"></h1>
                    <#nested "show-username">
                    <div class="ifx-attempted-user">
                        <span>${auth.attemptedUsername}</span>
                        <a href="${url.loginRestartFlowUrl}">${msg("restartLoginTooltip")}</a>
                    </div>
                </#if>

                <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
                    <div class="ifx-alert ifx-alert--${message.type}" role="alert">
                        ${kcSanitize(message.summary)?no_esc}
                    </div>
                </#if>

                <#nested "form">

                <#if auth?has_content && auth.showTryAnotherWayLink()>
                    <form id="kc-select-try-another-way-form" action="${url.loginAction}" method="post">
                        <input type="hidden" name="tryAnotherWay" value="on"/>
                        <a href="#" class="ifx-link" onclick="document.forms['kc-select-try-another-way-form'].requestSubmit();return false;">${msg("doTryAnotherWay")}</a>
                    </form>
                </#if>

                <#if displayInfo>
                    <div class="ifx-card__info">
                        <#nested "info">
                    </div>
                </#if>

                <#nested "socialProviders">
            </div>
        </main>
    </#if>

    <footer class="ifx-footer">
        <p class="ifx-footer__caption">Avalado por</p>

        <div class="ifx-footer__row">
            <img src="${appUrl}/Logo_UTEC.png" alt="Logo de UTEC" width="90" height="85">
            <img src="${appUrl}/Logo_CURE.png" alt="Logo de CURE" width="120" height="60">
            <img src="${appUrl}/Logo_UDELAR.png" alt="Logo de UDELAR" width="90" height="65">
            <img src="${appUrl}/Logo_UTU1.png" alt="Logo de UTU" width="160" height="60">
        </div>

        <div class="ifx-footer__row ifx-footer__row--second">
            <img src="${appUrl}/Logo_MIDES.png" alt="Logo de MIDES" width="110" height="55">
            <img src="${appUrl}/Logo_MITURISMO.png" alt="Logo de Ministerio de Turismo" width="110" height="55">
            <img src="${appUrl}/LOGO_MIEM.jpg" alt="Logo de MIEM" width="110" height="55">
            <img src="${appUrl}/Logo_PROBIDES.png" alt="Logo de PROBIDES" width="100" height="55">
            <img src="${appUrl}/Logo_INEFOP.png" alt="Logo de INEFOP" width="100" height="55">
            <img src="${appUrl}/Logo_LATITUD.png" alt="Logo de Latitud" width="100" height="55">
        </div>
    </footer>

</body>
</html>
</#macro>
