<#-- Correo con el código del segundo factor (autenticador email-otp) -->
<#import "template.ftl" as layout>
<@layout.emailLayout>
<p>${msg("emailCodeGreeting", (user.firstName)!"")}</p>
<p>${msg("emailCodeIntro", realmName)}</p>
<p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; font-family: monospace; margin: 24px 0;">${code}</p>
<p>${msg("emailCodeExpiration", ttlMinutes)}</p>
<p style="color: #737373; font-size: 13px;">${msg("emailCodeIgnore")}</p>
</@layout.emailLayout>
