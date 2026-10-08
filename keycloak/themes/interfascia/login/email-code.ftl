<#-- Segundo paso del login: código de 6 dígitos enviado por correo (autenticador email-otp) -->
<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=true displayInfo=false; section>
    <#if section = "header">
        ${msg("emailCodeTitle")}
    <#elseif section = "form">
        <p class="ifx-card__info">${msg("emailCodeInstruction", emailEnmascarado!"")}</p>

        <form id="kc-email-code-form" class="ifx-form" action="${url.loginAction}" method="post">
            <div class="ifx-field">
                <label for="code">${msg("emailCodeLabel")}</label>
                <input id="code" name="code" type="text" inputmode="numeric" pattern="[0-9]{6}" maxlength="6"
                       autocomplete="one-time-code" autofocus required dir="ltr"
                       data-etiqueta-digito="${msg("emailCodeDigit")}"
                       aria-invalid="<#if message?has_content && message.type == 'error'>true</#if>" />
            </div>

            <button class="ifx-submit ifx-submit--login" name="login" type="submit">${msg("emailCodeSubmit")}</button>
        </form>
        <#-- Sin defer: arma las 6 cajas antes de que cargue required-fields.js -->
        <script src="${url.resourcesPath}/js/codigo-cajas.js?v=${properties.recursosVersion!'1'}"></script>

        <#-- Formulario aparte: el reenvío no necesita el campo "code" (que es required) -->
        <form id="kc-email-code-resend" action="${url.loginAction}" method="post">
            <input type="hidden" name="resend" value="true" />
            <button class="ifx-link ifx-link--center ifx-link--button" type="submit">${msg("emailCodeResend")}</button>
        </form>
    </#if>
</@layout.registrationLayout>
