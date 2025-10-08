'use client';

import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/app/components/ui/card';
import { ToolCase, ArrowRight } from 'lucide-react';
import AppHeader from '@/app/components/AppHeader';

export default function HomePage() {
  return (
    <>
      <div className="flex justify-center px-4">
        <div className="w-full max-w-7xl">
          <AppHeader 
            title="Painel Administrativo" 
            subtitle="Navegue pelas seções."
          />
        </div>
      </div>
      <div className="flex justify-center px-4 pb-6">
        <div className="w-full max-w-7xl">
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <Link href="/servicos" className="group">
            <Card className="h-full transition-all duration-200 ease-in-out hover:border-primary hover:shadow-lg">
              <CardHeader>
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <ToolCase className="h-6 w-6" />
                </div>
                <CardTitle>Painel de Serviços</CardTitle>
                <CardDescription>
                  Ver Serviços.
                </CardDescription>
              </CardHeader>
              <CardContent>
                  <div className="flex items-center text-sm font-medium text-primary">
                      Ir para serviços
                      <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </div>
              </CardContent>
            </Card>
          </Link>
          </div>
        </div>
      </div>
    </>
  );
}
