<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username','password') displayInfo=true; section>
    <#if section = "header">
        <p class="ifx-eyebrow">${msg("loginEyebrow")}</p>
        <h1 class="ifx-title">${msg("loginAccountTitle")}</h1>
        <p class="ifx-lede">${msg("loginLede")}</p>
    <#elseif section = "form">
        <#if realm.password>
            <form id="kc-form-login" class="ifx-form" action="${url.loginAction}" method="post" novalidate>

                <#-- Lo pone el autenticador auth-username-password-form-intentos cuando la cuenta está bloqueada -->
                <#if bloqueoMinutos??>
                    <div class="ifx-bloqueo" role="alert">
                        <svg class="ifx-bloqueo__icono" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                            <rect x="4" y="11" width="16" height="10" rx="2"/>
                            <path d="M8 11V7a4 4 0 0 1 8 0v4"/>
                        </svg>
                        <span>${kcSanitize(messagesPerField.getFirstError('username','password'))?no_esc}</span>
                    </div>
                </#if>

                <#if !usernameHidden??>
                    <div class="ifx-field">
                        <label for="username">${msg("usernameOrEmail")}</label>
                        <input id="username" name="username" type="text" value="${(login.username!'')}"
                               autofocus autocomplete="username" dir="ltr" required
                               aria-invalid="<#if messagesPerField.existsError('username','password')>true</#if>" />
                    </div>
                </#if>

                <div class="ifx-field">
                    <label for="password">${msg("password")}</label>
                    <input id="password" name="password" type="password" autocomplete="current-password" required
                           aria-invalid="<#if messagesPerField.existsError('username','password')>true</#if>" />
                </div>

                <#if messagesPerField.existsError('username','password') && !bloqueoMinutos??>
                    <span class="ifx-field__error" aria-live="polite">
                        ${kcSanitize(messagesPerField.getFirstError('username','password'))?no_esc}
                    </span>
                </#if>

                <#-- Contador: un punto por intento permitido, los usados quedan apagados -->
                <#if intentosRestantes?? && intentosPermitidos??>
                    <div class="ifx-intentos" aria-hidden="true">
                        <span>${msg("intentosRestantesLabel")}</span>
                        <span class="ifx-intentos__puntos">
                            <#list 1..intentosPermitidos as i>
                                <span class="ifx-intentos__punto<#if i <= intentosRestantes> ifx-intentos__punto--libre</#if>"></span>
                            </#list>
                        </span>
                        <strong>${intentosRestantes}/${intentosPermitidos}</strong>
                    </div>
                </#if>

                <#if realm.resetPasswordAllowed>
                    <a class="ifx-link" href="${url.loginResetCredentialsUrl}">${msg("doForgotPassword")}</a>
                </#if>

                <input type="hidden" id="id-hidden-input" name="credentialId" <#if auth.selectedCredential?has_content>value="${auth.selectedCredential}"</#if>/>
                <button class="ifx-submit ifx-submit--login" name="login" id="kc-login" type="submit">${msg("doLogIn")}</button>

            </form>
        </#if>
    <#elseif section = "info">
        <#if realm.registrationAllowed && !registrationDisabled??>
            <#-- Por la app (no url.registrationUrl) para que el registro termine en el aviso de éxito -->
            <p class="ifx-account">${msg("noAccount")} <a href="${(properties.appUrl!'http://localhost:3000')?remove_ending('/')}/registro">${msg("registerNow")}</a></p>
        </#if>
    <#elseif section = "socialProviders">
        <#if realm.password && social?? && social.providers?has_content>
            <div class="ifx-social">
                <#list social.providers as p>
                    <a class="ifx-social__button" id="social-${p.alias}" href="${p.loginUrl}">
                        <#if p.alias == "google">
                            <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
                                <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34.2 6.1 29.4 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.5-.4-3.5z"/>
                                <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34.2 6.1 29.4 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>
                                <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.3 26.7 36 24 36c-5.3 0-9.7-3.3-11.3-7.9l-6.5 5C9.6 39.6 16.2 44 24 44z"/>
                                <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.1-4.1 5.5l.1.1 6.2 5.2C39.2 37.1 44 32 44 24c0-1.3-.1-2.5-.4-3.5z"/>
                            </svg>
                        </#if>
                        Continuar con ${p.displayName!}
                    </a>
                </#list>
            </div>
        </#if>
    </#if>
</@layout.registrationLayout>
