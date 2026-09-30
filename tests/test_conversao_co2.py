import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experimentos.validar_conversao_co2 import (
    CONSUMO, EMISSAO, analisar, converter_consumo, main, verificar_unidades,
)
from vtcpfm import consumo_trecho_vtcpfm


class ConversaoCO2Test(unittest.TestCase):
    def criar_csv(self, registros, campos=None):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        caminho = Path(pasta.name) / 'dados.csv'
        with caminho.open('w', encoding='utf-8', newline='') as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(campos or ['Fuel Type', CONSUMO, EMISSAO])
            escritor.writerows(registros)
        return caminho

    def test_unidades_e_entrada_invalida(self):
        self.assertEqual(converter_consumo(10, 2700), (0.1, 270))
        self.assertEqual(converter_consumo(0), (0, 0))
        for consumo in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                converter_consumo(consumo)
        for fator in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                converter_consumo(10, fator)
        self.assertTrue(all(v['passou'] for v in verificar_unidades()))

    def test_integracao_com_vazao_controlada(self):
        # 1 mL/s por 100 s = 0.1 L em 1 km a 36 km/h.
        # Isola a conversão de unidades da equação de potência/consumo.
        with patch('vtcpfm.vazao_combustivel', return_value=0.001):
            resultado = consumo_trecho_vtcpfm(1000, 0, altitude_m=0, velocidade_kmh=36)
        self.assertAlmostEqual(resultado.combustivel_l, 0.1)
        self.assertAlmostEqual(resultado.co2_g, 269.71966545766954)

    def test_filtro_diesel_rejeicoes_e_estatisticas(self):
        caminho = self.criar_csv([
            ['D', 10, 270], ['D', 20, 560], ['X', 10, 230],
            ['D', 0, 100], ['D', 'nan', 100], ['D', 10, ''],
        ])
        resumo, detalhes = analisar(caminho)
        self.assertEqual(resumo['registros_total'], 6)
        self.assertEqual(resumo['registros_diesel'], 5)
        self.assertEqual(resumo['registros_validos'], 2)
        self.assertEqual(len(resumo['registros_rejeitados']), 3)
        self.assertEqual(resumo['fator_implicito_media_g_l'], 2750)
        self.assertEqual(resumo['fator_implicito_mediana_g_l'], 2750)
        self.assertEqual(detalhes[0]['linha_csv'], 2)

    def test_sem_diesel_ou_colunas_ausentes(self):
        for caminho in (self.criar_csv([['X', 10, 230]]),
                        self.criar_csv([['D', 0, 100]]),
                        self.criar_csv([], ['Fuel Type'])):
            with self.assertRaises(ValueError):
                analisar(caminho)

    def test_exportacao(self):
        caminho = self.criar_csv([['D', 10, 270]])
        saida = caminho.parent / 'resultados'
        with patch('builtins.print'):
            self.assertEqual(main(['--dataset', str(caminho), '--saida', str(saida)]), 0)
        resumo = json.loads((saida / 'resumo.json').read_text(encoding='utf-8'))
        self.assertEqual(len(resumo['sha256']), 64)
        self.assertEqual(resumo['registros_validos'], 1)
        self.assertTrue((saida / 'diesel.csv').is_file())
        self.assertTrue((saida / 'relatorio.md').is_file())


if __name__ == '__main__':
    unittest.main()
