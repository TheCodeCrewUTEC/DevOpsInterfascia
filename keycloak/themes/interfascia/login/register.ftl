<#import "template.ftl" as layout>
<#import "register-commons.ftl" as registerCommons>

<#-- Atributos del perfil de usuario indexados por nombre -->
<#assign attrs = {}>
<#list profile.attributes as a>
    <#assign attrs = attrs + {a.name: a}>
</#list>

<#assign departamentos = ["Artigas", "Canelones", "Cerro Largo", "Colonia", "Durazno", "Flores", "Florida", "Lavalleja", "Maldonado", "Montevideo", "Paysandú", "Río Negro", "Rivera", "Rocha", "Salto", "San José", "Soriano", "Tacuarembó", "Treinta y Tres"]>
<#assign institucionesOpciones = ["UTEC", "UDELAR", "CURE", "UTU", "ANII", "Otra"]>
<#assign rolesOpciones = ["Investigador", "Inversor", "Emprendedor", "Estudiante", "Docente", "Otro"]>

<#function opciones attribute>
    <#if attribute?? && attribute.validators?? && attribute.validators.options?? && attribute.validators.options.options??>
        <#return attribute.validators.options.options>
    </#if>
    <#return []>
</#function>

<#function valoresDe attribute>
    <#assign lista = []>
    <#if attribute?? && attribute.values??>
        <#list attribute.values as valor>
            <#if valor?has_content>
                <#assign lista = lista + [valor]>
            </#if>
        </#list>
    </#if>
    <#if !lista?has_content>
        <#assign lista = [""]>
    </#if>
    <#return lista>
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

<#macro textField name type="text" required=false autocomplete="">
    <#assign attribute = attrs[name]!>
    <#assign isRequired = required>
    <#assign value = "">
    <#assign readOnly = false>
    <#assign auto = autocomplete>
    <#if attrs[name]??>
        <#assign isRequired = attribute.required!required>
        <#assign value = attribute.value!''>
        <#assign readOnly = attribute.readOnly!false>
        <#if attribute.autocomplete??>
            <#assign auto = attribute.autocomplete>
        </#if>
    </#if>
    <div class="ifx-field ifx-field--compact">
        <label for="${name}">${msg(name)}<#if isRequired>*</#if></label>
        <input id="${name}" name="${name}" type="${type}" value="${value}"
               <#if auto?has_content>autocomplete="${auto}"</#if>
               <#if isRequired>required</#if>
               <#if readOnly>disabled</#if>
               aria-invalid="<#if messagesPerField.existsError(name)>true</#if>" />
        <@fieldError name/>
    </div>
</#macro>

<#macro passwordField name labelKey autocomplete="new-password">
    <div class="ifx-field ifx-field--compact">
        <label for="${name}">${msg(labelKey)}*</label>
        <input id="${name}" name="${name}" type="password" autocomplete="${autocomplete}" required
               aria-invalid="<#if messagesPerField.existsError(name)>true</#if>" />
        <@fieldError name/>
    </div>
</#macro>

<#macro selectField name placeholderKey required=true fallback="">
    <#assign attribute = attrs[name]!>
    <#assign valor = "">
    <#assign isRequired = required>
    <#assign opts = fallback?is_sequence?then(fallback, [])>
    <#if attrs[name]??>
        <#assign valor = attribute.value!''>
        <#assign isRequired = attribute.required!required>
        <#assign desdePerfil = opciones(attribute)>
        <#if desdePerfil?has_content>
            <#assign opts = desdePerfil>
        </#if>
    </#if>
    <div class="ifx-field ifx-field--compact">
        <label for="${name}">${msg(name)}<#if isRequired>*</#if></label>
        <select id="${name}" name="${name}" <#if isRequired>required</#if>
                aria-invalid="<#if messagesPerField.existsError(name)>true</#if>">
            <option value="" disabled <#if !valor?has_content>selected</#if>>${msg(placeholderKey)}</option>
            <#list opts as opcion>
                <option value="${opcion}" <#if opcion == valor>selected</#if>>${opcion}</option>
            </#list>
        </select>
        <@fieldError name/>
    </div>
</#macro>

<#-- Select con botón "+" para agregar más valores (atributos multivaluados) -->
<#macro addableSelect name placeholderKey required=true fallback="">
    <#assign attribute = attrs[name]!>
    <#assign isRequired = required>
    <#assign opts = fallback?is_sequence?then(fallback, [])>
    <#assign valores = [""]>
    <#if attrs[name]??>
        <#assign isRequired = attribute.required!required>
        <#assign desdePerfil = opciones(attribute)>
        <#if desdePerfil?has_content>
            <#assign opts = desdePerfil>
        </#if>
        <#assign valores = valoresDe(attribute)>
    </#if>
    <div class="ifx-field ifx-field--compact" data-addable-select>
        <label for="${name}-0">${msg(name)}<#if isRequired>*</#if></label>
        <#list valores as valor>
            <div class="ifx-addable__row">
                <select id="${name}-${valor?index}" name="${name}"
                        <#if isRequired && valor?is_first>required</#if>
                        aria-invalid="<#if messagesPerField.existsError(name)>true</#if>">
                    <option value="" disabled <#if !valor?has_content>selected</#if>>${msg(placeholderKey)}</option>
                    <#list opts as opcion>
                        <option value="${opcion}" <#if opcion == valor>selected</#if>>${opcion}</option>
                    </#list>
                </select>
                <button type="button" class="ifx-addable__add" aria-label="${msg('agregarOtro')}">+</button>
            </div>
        </#list>
        <@fieldError name/>
    </div>
</#macro>

<@layout.registrationLayout displayMessage=messagesPerField.exists('global') variant="page"; section>
    <#if section = "form">
        <div class="ifx-register">

            <aside class="ifx-register__aside">
                <div class="ifx-blob" aria-hidden="true"></div>
                <p class="ifx-eyebrow">${msg("registerEyebrow")}</p>
                <h2 class="ifx-title">${msg("registerAsideTitle")}</h2>
                <p class="ifx-lede">${msg("registerAsideText")}</p>
                <ol class="ifx-steps">
                    <li class="ifx-step">
                        <span class="ifx-step__num">01</span>
                        <p class="ifx-step__title">${msg("registerStep1Title")}</p>
                        <p class="ifx-step__text">${msg("registerStep1Text")}</p>
                    </li>
                    <li class="ifx-step">
                        <span class="ifx-step__num">02</span>
                        <p class="ifx-step__title">${msg("registerStep2Title")}</p>
                        <p class="ifx-step__text">${msg("registerStep2Text")}</p>
                    </li>
                    <li class="ifx-step">
                        <span class="ifx-step__num">03</span>
                        <p class="ifx-step__title">${msg("registerStep3Title")}</p>
                        <p class="ifx-step__text">${msg("registerStep3Text")}</p>
                    </li>
                </ol>
            </aside>

            <section class="ifx-register__panel">
                <p class="ifx-required-alert" data-required-banner hidden role="alert">${msg("requiredFieldsAlert")}</p>
                <h1 class="ifx-title">${msg("registerTitle")}</h1>
                <p class="ifx-hint">${msg("registerHint")}</p>

                <#if message?has_content && messagesPerField.exists('global')>
                    <div class="ifx-alert ifx-alert--${message.type}" role="alert">
                        ${kcSanitize(message.summary)?no_esc}
                    </div>
                </#if>

                <form id="kc-register-form" class="ifx-form ifx-form--compact" action="${url.registrationAction}" method="post" novalidate>

                    <#if attrs.locale?? && realm.internationalizationEnabled && locale.currentLanguageTag?has_content>
                        <input type="hidden" name="locale" value="${locale.currentLanguageTag}"/>
                    </#if>

                    <@textField name="firstName" required=true autocomplete="given-name"/>
                    <@textField name="lastName" required=true autocomplete="family-name"/>
                    <#if !realm.registrationEmailAsUsername>
                        <@textField name="username" required=true autocomplete="username"/>
                    </#if>
                    <@textField name="email" type="email" required=true autocomplete="email"/>

                    <@passwordField name="password" labelKey="password"/>
                    <@passwordField name="password-confirm" labelKey="passwordConfirm"/>

                    <@selectField name="departamentoResidencia" placeholderKey="seleccionaDepartamento" fallback=departamentos/>
                    <@addableSelect name="departamentosActuacion" placeholderKey="seleccionaDepartamento" fallback=departamentos/>
                    <@textField name="celular" type="tel" autocomplete="tel"/>
                    <@addableSelect name="instituciones" placeholderKey="seleccionaInstitucion" fallback=institucionesOpciones/>
                    <@addableSelect name="perfil" placeholderKey="seleccionaRol" fallback=rolesOpciones/>

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

                    <p class="ifx-account">${msg("alreadyHaveAccount")} <a href="${url.loginUrl}">${msg("doLogIn")}</a></p>
                </form>
            </section>

        </div>
        <script src="${url.resourcesPath}/js/addable-select.js" defer></script>
    </#if>
</@layout.registrationLayout>
