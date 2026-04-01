# scripts/test_env.py

from src.config import settings

print("🔍 Verificando variáveis de ambiente...\n")

checks = {
    "SUPABASE_URL": settings.supabase_url,
    "SUPABASE_KEY": settings.supabase_key[:20] + "..." if settings.supabase_key else "❌ VAZIO",
    "SUPABASE_ANON_KEY": settings.supabase_anon_key[:20] + "..." if settings.supabase_anon_key else "⏭️ Opcional",
    "APP_NAME": settings.app_name,
    "DEBUG": settings.debug,
    "LOG_LEVEL": settings.log_level,
}

all_ok = True
for key, value in checks.items():
    status = "✅" if value else "❌"
    print(f"  {status} {key}: {value}")
    if not value and key in ("SUPABASE_URL", "SUPABASE_KEY"):
        all_ok = False

print(f"\n{'🎉 Tudo configurado!' if all_ok else '⚠️ Preencha os campos faltantes no .env'}")
