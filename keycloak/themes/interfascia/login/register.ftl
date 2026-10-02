<#import "template.ftl" as layout>
<#import "register-commons.ftl" as registerCommons>

<#-- Atributos del perfil de usuario indexados por nombre -->
<#assign attrs = {}>
<#list profile.attributes as a>
    <#assign attrs = attrs + {a.name: a}>
</#list>

<#function opciones attribute>
    <#if attribute.validators.options?? && attribute.validators.options.options??>
        <#return attribute.validators.options.options>
    </#if>
    <#return []>
</#function>

<#macro fieldError name>
    <#if messagesPerField.existsError(name)>
        <span id="input-error-${name}" class="ifx-field__error" aria-live="polite">
            ${kcSanitize(messagesPerField.get(name))?no_esc}
        </span>
    </#if>
</#macro>

<#macro label attribute forId="">
    <label for="${forId?has_content?then(forId, attribute.name)}">${advancedMsg(attribute.displayName!attribute.name)}<#if attribute.required>*</#if></label>
</#macro>

<#macro textField name type="text">
    <#if attrs[name]??>
        <#assign attribute = attrs[name]>
        <div class="ifx-field ifx-field--compact">
            <@label attribute=attribute/>
            <input id="${attribute.name}" name="${attribute.name}" type="${type}" value="${(attribute.value!'')}"
                   <#if attribute.autocomplete??>autocomplete="${attribute.autocomplete}"</#if>
                   <#if attribute.required>required</#if>
                   <#if attribute.readOnly>disabled</#if>
                   aria-invalid="<#if messagesPerField.existsError(attribute.name)>true</#if>" />
            <@fieldError attribute.name/>
        </div>
    </#if>
</#macro>

<#macro passwordField name labelKey autocomplete="new-password">
    <div class="ifx-field ifx-field--compact">
        <label for="${name}">${msg(labelKey)}*</label>
        <input id="${name}" name="${name}" type="password" autocomplete="${autocomplete}" required
               aria-invalid="<#if messagesPerField.existsError(name)>true</#if>" />
        <@fieldError name/>
    </div>
</#macro>

<#macro selectField name placeholderKey>
    <#if attrs[name]??>
        <#assign attribute = attrs[name]>
        <#assign valor = attribute.value!''>
        <div class="ifx-field ifx-field--compact">
            <@label attribute=attribute/>
            <select id="${attribute.name}" name="${attribute.name}" <#if attribute.required>required</#if>
                    aria-invalid="<#if messagesPerField.existsError(attribute.name)>true</#if>">
                <option value="" disabled <#if !valor?has_content>selected</#if>>${msg(placeholderKey)}</option>
                <#list opciones(attribute) as opcion>
                    <option value="${opcion}" <#if opcion == valor>selected</#if>>${opcion}</option>
                </#list>
            </select>
            <@fieldError attribute.name/>
        </div>
    </#if>
</#macro>

<#-- Select con botón "+" para agregar más valores (atributos multivaluados) -->
<#macro addableSelect name placeholderKey>
    <#if attrs[name]??>
        <#assign attribute = attrs[name]>
        <#assign valores = (attribute.values![])?filter(v -> v?has_content)>
        <#if !valores?has_content>
            <#assign valores = [""]>
        </#if>
        <div class="ifx-field ifx-field--compact" data-addable-select>
            <@label attribute=attribute forId="${attribute.name}-0"/>
            <#list valores as valor>
                <div class="ifx-addable__row">
                    <select id="${attribute.name}-${valor?index}" name="${attribute.name}"
                            <#if attribute.required && valor?is_first>required</#if>
                            aria-invalid="<#if messagesPerField.existsError(attribute.name)>true</#if>">
                        <option value="" disabled <#if !valor?has_content>selected</#if>>${msg(placeholderKey)}</option>
                        <#list opciones(attribute) as opcion>
                            <option value="${opcion}" <#if opcion == valor>selected</#if>>${opcion}</option>
                        </#list>
                    </select>
                    <button type="button" class="ifx-addable__add" aria-label="${msg('agregarOtro')}">+</button>
                </div>
            </#list>
            <@fieldError attribute.name/>
        </div>
    </#if>
</#macro>

<@layout.registrationLayout displayMessage=messagesPerField.exists('global') variant="page"; section>
    <#if section = "form">
        <div class="ifx-register">

            <div class="ifx-register__image" aria-hidden="true">
                <span>&#10005;</span>
            </div>

            <div>
                <h1 class="ifx-register__title">${msg("registerTitle")}</h1>

                <#if message?has_content && messagesPerField.exists('global')>
                    <div class="ifx-alert ifx-alert--${message.type}" role="alert">
                        ${kcSanitize(message.summary)?no_esc}
                    </div>
                </#if>

                <form id="kc-register-form" class="ifx-form ifx-form--compact" action="${url.registrationAction}" method="post">

                    <#if attrs.locale?? && realm.internationalizationEnabled && locale.currentLanguageTag?has_content>
                        <input type="hidden" name="locale" value="${locale.currentLanguageTag}"/>
                    </#if>

                    <@textField name="firstName"/>
                    <@textField name="lastName"/>
                    <#if !realm.registrationEmailAsUsername>
                        <@textField name="username"/>
                    </#if>
                    <@textField name="email" type="email"/>

                    <#if passwordRequired??>
                        <@passwordField name="password" labelKey="password"/>
                        <@passwordField name="password-confirm" labelKey="passwordConfirm"/>
                    </#if>

                    <@selectField name="departamentoResidencia" placeholderKey="seleccionaDepartamento"/>
                    <@addableSelect name="departamentosActuacion" placeholderKey="seleccionaDepartamento"/>
                    <@textField name="celular" type="tel"/>
                    <@addableSelect name="instituciones" placeholderKey="seleccionaInstitucion"/>
                    <@addableSelect name="perfil" placeholderKey="seleccionaRol"/>

                    <#-- Cualquier atributo que se agregue después al perfil de usuario se muestra igual -->
                    <#assign conocidos = ["locale", "username", "email", "firstName", "lastName", "departamentoResidencia", "departamentosActuacion", "celular", "instituciones", "perfil"]>
                    <#list profile.attributes as a>
                        <#if !conocidos?seq_contains(a.name)>
                            <@textField name=a.name/>
                        </#if>
                    </#list>

                    <@registerCommons.termsAcceptance/>

                    <#if recaptchaRequired?? && (recaptchaVisible!false)>
                        <div class="g-recaptcha" data-size="compact" data-sitekey="${recaptchaSiteKey}" data-action="${recaptchaAction}"></div>
                    </#if>

                    <button class="ifx-submit ifx-submit--register" type="submit">${msg("doRegister")}</button>
                </form>
            </div>

        </div>
        <script src="${url.resourcesPath}/js/addable-select.js" defer></script>
    </#if>
</@layout.registrationLayout>
