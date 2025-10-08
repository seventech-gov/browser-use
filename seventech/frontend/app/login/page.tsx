'use client';

import { useState, Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/app/contexts/AuthContext';
import { systemApi } from '@/app/services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/app/components/ui/card';
import { Label } from '@/app/components/ui/label';
import { Button } from '@/app/components/ui/button';
import { Input } from '@/app/components/ui/input';
import { Alert, AlertDescription } from '@/app/components/ui/alert';
import { Eye, EyeOff, Moon, Sun, Terminal, Loader2 } from 'lucide-react';
import { useTheme } from 'next-themes';

function LoginForm() {
  const [token, setToken] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showToken, setShowToken] = useState(false);
  const { login } = useAuth();
  const { resolvedTheme, setTheme } = useTheme();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const toggleTheme = () => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    // Para desenvolvimento, aceitar qualquer token não vazio
    // ou permitir login sem token
    if (!token.trim()) {
      // Login sem token para desenvolvimento
      const devToken = 'dev-token-' + Date.now();
      try {
        const authResult = await systemApi.auth();
        if (authResult.status === 'authenticated') {
          login(devToken);
          const redirectUrl = searchParams.get('redirect_url');
          router.push(redirectUrl || '/');
          return;
        }
      } catch {
        setError('Falha na autenticação. Servidor pode estar offline.');
        setIsLoading(false);
        return;
      }
    }

    try {
      // Tentar autenticar com o token fornecido
      const authResult = await systemApi.auth();
      if (authResult.status === 'authenticated') {
        login(token);
        const redirectUrl = searchParams.get('redirect_url');
        router.push(redirectUrl || '/');
      } else {
        throw new Error('Autenticação falhou');
      }
    } catch {
      setError('Falha na autenticação. Verifique se o servidor está rodando.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md relative border shadow-2xl">
        <CardHeader className="text-center p-8">
          <div className="absolute top-4 right-4">
          {mounted && (
            <Button onClick={toggleTheme} variant="ghost" size="icon" className="border" title={`Mudar para tema ${resolvedTheme === 'light' ? 'escuro' : 'claro'}`}>
              {resolvedTheme === 'dark' ? (
                <Sun className="h-[1.2rem] w-[1.2rem]" />
              ) : (
                <Moon className="h-[1.2rem] w-[1.2rem]" />
              )}
              <span className="sr-only">Toggle theme</span>
            </Button>
          )}
        </div>
          <CardTitle className="text-3xl font-bold tracking-tight">SevenTech Login</CardTitle>
          <CardDescription className="text-muted-foreground pt-2">
            Insira um token ou deixe vazio para desenvolvimento.
          </CardDescription>
        </CardHeader>
        <CardContent className="px-8 pb-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="token-input">Bearer Token</Label>
              <div className="relative">
                <Input
                  id="token-input"
                  type={showToken ? 'text' : 'password'}
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Token opcional (deixe vazio para dev)"
                  className="pr-10 transition-shadow focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-auto px-2 py-1 text-muted-foreground"
                  onClick={() => setShowToken(!showToken)}
                  title={showToken ? 'Ocultar token' : 'Mostrar token'}
                >
                  {showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>
            
            {error && (
              <Alert className="border-destructive text-destructive">
                <Terminal className="h-4 w-4"/>
                <AlertDescription className="text-destructive">
                  {error}
                </AlertDescription>
              </Alert>
            )}
            
            <Button 
              type="submit" 
              disabled={isLoading} 
              className="w-full font-bold bg-emerald-600 hover:bg-emerald-700 text-white transition-all duration-200 ease-in-out hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 mt-4" 
              size="lg"
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isLoading ? 'Validando...' : 'Entrar'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center">Carregando...</div>}>
      <LoginForm />
    </Suspense>
  );
}
