<#--
  Plantilla base del tema Interfascia.
  Replica el navbar y el footer de la app Next.js para que el login no parezca otro sitio.
  variant="card"  -> tarjeta blanca centrada sobre el fondo de la app (login, recuperar contraseña, errores...)
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
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Geist:wght@400;500;600&display=swap" rel="stylesheet" />
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
        <div class="ifx-navbar__inner">
            <a class="ifx-navbar__brand" href="${appUrl}/">
                <span class="ifx-navbar__mark" aria-hidden="true">
                    <svg width="18" height="18" viewBox="0 0 18 18">
                        <circle cx="5" cy="9" r="2.2" fill="currentColor" />
                        <circle cx="13" cy="5" r="2.2" fill="#f26b3a" />
                        <circle cx="13" cy="13" r="2.2" fill="#ffffff" />
                        <path d="M7 8.2 11 5.8M7 9.8 11 12.2" stroke="currentColor" stroke-width="1.2" />
                    </svg>
                </span>
                <span class="ifx-navbar__name">Interfascia</span>
            </a>

            <div class="ifx-navbar__links">
                <a href="${appUrl}/repositorio">Repositorio</a>
                <a href="${appUrl}/#que-es-interfascia">¿Qué es Interfascia?</a>
                <a href="${appUrl}/consultor-ia">Consultor IA</a>
                <a href="${appUrl}/analisis-datos">Análisis de Datos</a>
            </div>

            <#-- Pasan por la app: así el registro siempre termina en el aviso de "Registro exitoso" -->
            <div class="ifx-navbar__actions">
                <a class="ifx-btn ifx-btn--primary" href="${appUrl}/login">Iniciar sesión</a>
                <#if realm.registrationAllowed>
                    <a class="ifx-btn ifx-btn--secondary" href="${appUrl}/registro">Registrate</a>
                </#if>
            </div>
        </div>
    </nav>

    <#-- El registro no comparte la tarjeta de login: es una página aparte -->
    <#if variant == "page" || (pageId!"") == "register">
        <main class="ifx-page">
            <#nested "form">
        </main>
    <#else>
        <main class="ifx-overlay">
            <div class="ifx-blob ifx-blob--gold" aria-hidden="true"></div>
            <div class="ifx-blob ifx-blob--pine" aria-hidden="true"></div>
            <div class="ifx-card">
                <a href="${appUrl}/" class="ifx-card__close" aria-label="Cerrar">&times;</a>
                <p class="ifx-required-alert" data-required-banner hidden role="alert">${msg("requiredFieldsAlert")}</p>

                <#if !(auth?has_content && auth.showUsername() && !auth.showResetCredentials())>
                    <div class="ifx-card__intro"><#nested "header"></div>
                <#else>
                    <div class="ifx-card__intro"><#nested "header"></div>
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

                <#nested "socialProviders">

                <#if displayInfo>
                    <div class="ifx-card__info">
                        <#nested "info">
                    </div>
                </#if>
            </div>
        </main>
    </#if>

    <footer class="ifx-footer">
        <div class="ifx-footer__inner">
            <p class="ifx-footer__caption">Avalado por</p>
            <p class="ifx-footer__note">Instituciones que acompañan el piloto en el territorio.</p>

            <div class="ifx-footer__rows">
                <div class="ifx-footer__row">
                    <div class="ifx-footer__logo"><img src="${appUrl}/Logo_UTEC.png" alt="Logo de UTEC"></div>
                    <div class="ifx-footer__logo"><img src="${appUrl}/Logo_CURE.png" alt="Logo de CURE"></div>
                    <div class="ifx-footer__logo"><img src="${appUrl}/Logo_UDELAR.png" alt="Logo de UDELAR"></div>
                    <div class="ifx-footer__logo"><img src="${appUrl}/Logo_UTU1.png" alt="Logo de UTU"></div>
                    <div class="ifx-footer__logo"><img src="${appUrl}/Logo_MIDES.png" alt="Logo de MIDES"></div>
                </div>
                <div class="ifx-footer__row">
                    <div class="ifx-footer__logo"><img src="${appUrl}/Logo_MITURISMO.png" alt="Logo de Ministerio de Turismo"></div>
                    <div class="ifx-footer__logo"><img src="${appUrl}/LOGO_MIEM.jpg" alt="Logo de MIEM"></div>
                    <div class="ifx-footer__logo"><img src="${appUrl}/Logo_PROBIDES.png" alt="Logo de PROBIDES"></div>
                    <div class="ifx-footer__logo"><img src="${appUrl}/Logo_INEFOP.png" alt="Logo de INEFOP"></div>
                    <div class="ifx-footer__logo"><img src="${appUrl}/Logo_LATITUD.png" alt="Logo de Latitud"></div>
                </div>
            </div>
        </div>
    </footer>

    <script src="${url.resourcesPath}/js/required-fields.js" defer></script>
</body>
</html>
</#macro>
