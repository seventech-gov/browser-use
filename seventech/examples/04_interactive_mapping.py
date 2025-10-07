"""Interactive mapping example - Map objectives that require user input.

This example shows how to use InteractiveMapper to handle objectives
that need dynamic user data (like CPF, inscrição imobiliária, etc.)
during the mapping process.

The mapper will pause and ask for input when needed, then continue.
"""

import asyncio
import logging

from browser_use.llm.google.chat import ChatGoogle
from dotenv import load_dotenv

from seventech.mapper.interactive import InteractiveMapper
from seventech.mapper.session import InputRequest
from seventech.mapper.views import MapObjectiveRequest, MapperConfig
from seventech.planner.service import Planner
from seventech.storage.service import Storage

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def input_callback(request: InputRequest) -> str:
	"""Callback to handle input requests during mapping.

	Args:
		request: Input request from mapper

	Returns:
		User-provided value
	"""
	print('\n' + '=' * 60)
	print('🤔 O MAPPER PRECISA DE AJUDA!')
	print('=' * 60)
	print(f'\nCampo: {request.field_label}')
	print(f'Descrição: {request.prompt}')

	if request.placeholder:
		print(f'Exemplo: {request.placeholder}')

	if request.xpath:
		print(f'XPath: {request.xpath}')

	print(f'Passo atual: {request.current_step}')
	print('-' * 60)

	# Get input from user
	value = input(f'\n✏️  Digite o valor para "{request.field_label}": ').strip()

	if not value and request.required:
		print('⚠️  Este campo é obrigatório!')
		return input_callback(request)  # Try again

	print(f'\n✅ Valor recebido: {value}')
	print('Continuando o mapeamento...\n')

	return value


async def main():
	"""Run interactive mapping example."""

	print('\n🎯 EXEMPLO DE MAPEAMENTO INTERATIVO\n')

	# Initialize LLM
	llm = ChatGoogle(model='gemini-2.0-flash-exp')

	# Create interactive mapper with callback
	mapper = InteractiveMapper(
		llm=llm,
		config=MapperConfig(
			headless=False,  # Must be visible for interactive mode
			max_steps=50,
			timeout_seconds=600,  # Longer timeout for interactive sessions
		),
		input_callback=input_callback,
	)

	# Define objective that will require user input
	# Example: A website that needs CPF or inscrição imobiliária
	request = MapObjectiveRequest(
		objective=(
			'Ir para https://iportal.rio.rj.gov.br/PF331IPTUATUAL/ '
			'e consultar o valor do IPTU. '
			'Quando encontrar o campo de inscrição imobiliária, '
			'peça ao usuário para fornecer o valor.'
		),
		tags=['iptu', 'rio', 'consulta'],
		plan_name='consulta_iptu_rio',
	)

	print('📋 Objetivo:')
	print(f'   {request.objective}\n')

	print('ℹ️  O mapper irá pausar quando precisar de dados do usuário.\n')
	input('Pressione ENTER para começar...')

	# Run interactive mapping
	print('\n🚀 Iniciando mapeamento interativo...\n')

	mapper_result, session = await mapper.map_objective(request)

	if not mapper_result.success:
		print(f'\n❌ Mapeamento falhou: {mapper_result.error_message}')
		return

	print('\n✅ Mapeamento concluído com sucesso!')
	print(f'\n📊 Resumo da Sessão:')
	print(f'   Session ID: {session.session_id}')
	print(f'   Status: {session.status.value}')
	print(f'   Parâmetros coletados: {len(session.collector.parameters)}')

	# Show collected parameters
	print('\n🔑 Parâmetros Coletados:')
	for param in session.get_collected_parameters():
		print(f'   • {param.label}')
		print(f'     Nome: {param.name}')
		print(f'     Valor: {param.value}')
		print(f'     XPath: {param.xpath or "N/A"}')
		print(f'     Exemplo: {param.example}')
		print()

	# Create plan from mapper result
	print('📝 Criando plano a partir do mapeamento...')
	planner = Planner()
	plan = planner.create_plan(mapper_result, plan_name=request.plan_name)

	print(f'\n✅ Plano criado!')
	print(f'   Plan ID: {plan.metadata.plan_id}')
	print(f'   Steps: {len(plan.steps)}')
	print(f'   Parâmetros necessários: {plan.metadata.required_params}')

	# Save plan
	storage = Storage()
	plan_id = storage.save_plan(plan)

	print(f'\n💾 Plano salvo: {plan_id}')
	print('\n🎉 Agora você pode executar este plano quantas vezes quiser,')
	print('   fornecendo os parâmetros coletados!')

	print(f'\n📋 Para executar:')
	print(f'   uv run python seventech/examples/02_execute_existing_plan.py')
	print(f'\n   Ou via API:')
	print(f'   curl -X POST http://localhost:8000/api/v1/execute/{plan_id} \\')
	print(f'     -H "Content-Type: application/json" \\')
	print(f'     -d \'{{"inscrição": "seu_valor_aqui"}}\'')


async def simple_example():
	"""Simpler example with direct console input."""

	print('\n🎯 EXEMPLO SIMPLES - Mapeamento Interativo\n')

	llm = ChatGoogle(model='gemini-2.0-flash-exp')

	# Interactive mapper without custom callback (uses default console input)
	mapper = InteractiveMapper(llm=llm, config=MapperConfig(headless=False))

	request = MapObjectiveRequest(
		objective='Ir para google.com e fazer uma busca. Se precisar de algum dado, pergunte ao usuário.',
		tags=['demo'],
	)

	mapper_result, session = await mapper.map_objective(request)

	if mapper_result.success:
		print(f'\n✅ Sucesso! Parâmetros coletados: {len(session.collector.parameters)}')
		for param in session.get_collected_parameters():
			print(f'   • {param.label}: {param.value}')
	else:
		print(f'\n❌ Falha: {mapper_result.error_message}')


if __name__ == '__main__':
	# Run the full example
	asyncio.run(main())

	# Or run the simple example:
	# asyncio.run(simple_example())
