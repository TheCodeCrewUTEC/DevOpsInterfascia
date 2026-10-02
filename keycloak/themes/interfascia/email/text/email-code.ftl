<#ftl output_format="plainText">
${msg("emailCodeGreeting", (user.firstName)!"")}

${msg("emailCodeIntro", realmName)}

${code}

${msg("emailCodeExpiration", ttlMinutes)}

${msg("emailCodeIgnore")}
