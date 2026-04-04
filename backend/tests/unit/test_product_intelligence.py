"""Product intelligence pipeline tests — pure logic, no database.

Tests the batch LLM path (Phase 1 decomposition + Phase 2 matching),
rule fallback, and helper functions.
"""
import json
import pytest
from catalog.application.product_intelligence import _agent_dict_to_analysis, _dict_to_analyzed_product, _normalize_pack_qty, _normalize_unit, _parse_llm_products, _rule_fallback, _validate_product, analyze_products
from catalog.domain.product_analysis import AnalyzedProduct, ProductAnalysis

class TestNormalizeUnit:

    def test_standard_units_pass_through(self):
        for unit in ('each', 'gallon', 'foot', 'pound', 'pack', 'box', 'roll'):
            assert _normalize_unit(unit) == unit

    def test_abbreviations_resolved(self):
        assert _normalize_unit('gal') == 'gallon'
        assert _normalize_unit('ft') == 'foot'
        assert _normalize_unit('lb') == 'pound'
        assert _normalize_unit('oz') == 'ounce'
        assert _normalize_unit('in') == 'inch'
        assert _normalize_unit('qt') == 'quart'
        assert _normalize_unit('sq ft') == 'sqft'
        assert _normalize_unit('pk') == 'pack'
        assert _normalize_unit('ea') == 'each'

    def test_unknown_defaults_to_each(self):
        assert _normalize_unit('widgets') == 'each'
        assert _normalize_unit('') == 'each'
        assert _normalize_unit(None) == 'each'
        assert _normalize_unit(42) == 'each'

class TestNormalizePackQty:

    def test_valid_int(self):
        assert _normalize_pack_qty(5) == 5
        assert _normalize_pack_qty(24) == 24

    def test_string_int(self):
        assert _normalize_pack_qty('12') == 12

    def test_none_defaults_to_1(self):
        assert _normalize_pack_qty(None) == 1

    def test_zero_or_negative_clamped(self):
        assert _normalize_pack_qty(0) == 1
        assert _normalize_pack_qty(-5) == 1

    def test_garbage_defaults_to_1(self):
        assert _normalize_pack_qty('abc') == 1

class TestParseLlmProducts:

    def test_valid_json_array(self):
        response = '[{"clean_name": "Widget", "base_unit": "each"}]'
        result = _parse_llm_products(response)
        assert len(result) == 1
        assert result[0]['clean_name'] == 'Widget'

    def test_json_with_surrounding_text(self):
        response = 'Here are the results:\n[{"clean_name": "A"}]\nDone.'
        result = _parse_llm_products(response)
        assert len(result) == 1

    def test_invalid_json_returns_empty(self):
        assert _parse_llm_products('not json at all') == []
        assert _parse_llm_products('[broken{json}') == []

    def test_empty_response_returns_empty(self):
        assert _parse_llm_products('') == []

class TestDictToAnalyzedProduct:

    def test_full_product(self):
        raw = {'raw_text': 'BrassCraft 3/8 in. supply line', 'clean_name': 'Braided Polymer Faucet Supply Line', 'brand': 'BrassCraft', 'product_type': 'faucet supply line', 'specifications': {'connection_a': '3/8 in.', 'length': '16 in.'}, 'base_unit': 'each', 'sell_uom': 'each', 'pack_qty': 1, 'suggested_department': 'PLU', 'variant_label': '16 in.', 'variant_attrs': {'length': '16 in.'}, 'original_sku': 'B1-16A F', 'confidence': 0.95}
        ap = _dict_to_analyzed_product(raw, 'fallback text')
        assert ap.clean_name == 'Braided Polymer Faucet Supply Line'
        assert ap.brand == 'BrassCraft'
        assert ap.base_unit == 'each'
        assert ap.suggested_department == 'PLU'
        assert ap.original_sku == 'B1-16A F'
        assert ap.confidence == 0.95
        assert ap.specifications['connection_a'] == '3/8 in.'

    def test_minimal_product(self):
        ap = _dict_to_analyzed_product({}, 'Some raw text')
        assert ap.raw_text == 'Some raw text'
        assert ap.clean_name == 'Some raw text'
        assert ap.base_unit == 'each'
        assert ap.suggested_department == 'HDW'
        assert ap.confidence == 0.0

    def test_unit_normalization_in_product(self):
        raw = {'base_unit': 'gal', 'sell_uom': 'qt', 'pack_qty': 5}
        ap = _dict_to_analyzed_product(raw, 'paint')
        assert ap.base_unit == 'gallon'
        assert ap.sell_uom == 'quart'
        assert ap.pack_qty == 5

    def test_confidence_clamped(self):
        ap = _dict_to_analyzed_product({'confidence': 1.5}, 'x')
        assert ap.confidence == 1.0
        ap = _dict_to_analyzed_product({'confidence': -0.5}, 'x')
        assert ap.confidence == 0.0

class TestAgentDictToAnalysis:

    def test_with_family_match(self):
        raw = {'clean_name': 'Faucet Supply Line', 'brand': 'BrassCraft', 'base_unit': 'each', 'sell_uom': 'each', 'pack_qty': 1, 'suggested_department': 'PLU', 'confidence': 0.95, 'matched_family_id': 'fam-123', 'matched_family_name': 'Faucet Supply Lines', 'matched_sku_id': 'sku-456', 'matched_vendor_item_id': 'vi-789', 'warnings': ['Check variant label']}
        result = _agent_dict_to_analysis(raw, {'name': 'BrassCraft supply line'})
        assert isinstance(result, ProductAnalysis)
        assert result.product.clean_name == 'Faucet Supply Line'
        assert result.matched_sku_id == 'sku-456'
        assert result.matched_vendor_item_id == 'vi-789'
        assert len(result.family_candidates) == 1
        assert result.family_candidates[0].family_id == 'fam-123'
        assert result.warnings == ['Check variant label']

    def test_without_family_match(self):
        raw = {'clean_name': 'New Widget', 'base_unit': 'each', 'sell_uom': 'each', 'suggested_department': 'HDW', 'confidence': 0.8}
        result = _agent_dict_to_analysis(raw, {'name': 'Widget'})
        assert result.family_candidates == []
        assert result.matched_sku_id is None

class TestRuleFallback:

    def test_pipe_inferred_as_foot(self):
        ap = _rule_fallback({'name': '1/2 in PEX Pipe 100ft'})
        assert ap.base_unit == 'foot'
        assert ap.pack_qty == 100
        assert ap.suggested_department == 'PLU'

    def test_paint_inferred_as_gallon(self):
        ap = _rule_fallback({'name': 'Sherwin-Williams Interior Latex Paint'})
        assert ap.base_unit == 'gallon'
        assert ap.suggested_department == 'PNT'

    def test_unknown_defaults_to_each(self):
        ap = _rule_fallback({'name': 'Mystery Widget'})
        assert ap.base_unit == 'each'
        assert ap.confidence == 0.3

    def test_screw_box_inferred(self):
        ap = _rule_fallback({'name': '#8 Wood Screw 1lb Box'})
        assert ap.base_unit in ('pound', 'box')

    def test_preserves_original_sku(self):
        ap = _rule_fallback({'name': 'Widget', 'original_sku': 'ABC-123'})
        assert ap.original_sku == 'ABC-123'

class TestValidateProduct:

    def test_no_warnings_for_good_product(self):
        ap = AnalyzedProduct(raw_text='Widget', clean_name='Nice Widget', base_unit='each', sell_uom='each', suggested_department='HDW', confidence=0.9)
        warnings = _validate_product(ap, {'HDW', 'PLU', 'ELE'})
        assert warnings == []

    def test_low_confidence_warning(self):
        ap = AnalyzedProduct(raw_text='Widget', clean_name='Widget', confidence=0.5)
        warnings = _validate_product(ap, {'HDW'})
        assert any(('Low confidence' in w for w in warnings))

    def test_unknown_department_warning(self):
        ap = AnalyzedProduct(raw_text='Widget', clean_name='Widget', suggested_department='XYZ', confidence=0.9)
        warnings = _validate_product(ap, {'HDW', 'PLU'})
        assert any(('Unknown department' in w for w in warnings))

    def test_name_not_cleaned_warning(self):
        ap = AnalyzedProduct(raw_text='messy raw text here', clean_name='messy raw text here', confidence=0.9)
        warnings = _validate_product(ap, {'HDW'})
        assert any(('manual cleanup' in w for w in warnings))

class TestBatchPipeline:

    @pytest.fixture
    def mock_llm_response(self):

        def generate_text(prompt, system_prompt=None):
            return json.dumps([{'raw_text': 'BrassCraft 3/8 in. Compression x 1/2 in. FIP x 16 in. Braided Polymer Faucet Supply Line', 'clean_name': 'Braided Polymer Faucet Supply Line', 'brand': 'BrassCraft', 'product_type': 'faucet supply line', 'specifications': {'connection_a': '3/8 in. Compression', 'connection_b': '1/2 in. FIP', 'length': '16 in.'}, 'base_unit': 'each', 'sell_uom': 'each', 'pack_qty': 1, 'suggested_department': 'PLU', 'variant_label': '16 in.', 'variant_attrs': {'length': '16 in.'}, 'original_sku': 'B1-16A F', 'confidence': 0.95}, {'raw_text': 'HDX 16 in. x 16 in. Multi-Purpose Microfiber Towel (24-Pack)', 'clean_name': 'Multi-Purpose Microfiber Towel', 'brand': 'HDX', 'product_type': 'cleaning towel', 'specifications': {'dimensions': '16 in. x 16 in.'}, 'base_unit': 'pack', 'sell_uom': 'pack', 'pack_qty': 24, 'suggested_department': 'HDW', 'variant_label': '24-Pack', 'variant_attrs': {'count': '24'}, 'original_sku': '2142099', 'confidence': 0.92}])
        return generate_text

    @pytest.mark.asyncio
    async def test_pipeline_with_llm(self, mock_llm_response):
        items = [{'name': 'BrassCraft 3/8 in. Compression x 1/2 in. FIP x 16 in. Braided Polymer Faucet Supply Line'}, {'name': 'HDX 16 in. x 16 in. Multi-Purpose Microfiber Towel (24-Pack)'}]
        results = await analyze_products(items, generate_text=mock_llm_response, dept_codes=['PLU', 'HDW', 'ELE', 'PNT'])
        assert len(results) == 2
        supply_line = results[0]
        assert isinstance(supply_line, ProductAnalysis)
        assert supply_line.product.clean_name == 'Braided Polymer Faucet Supply Line'
        assert supply_line.product.brand == 'BrassCraft'
        assert supply_line.product.base_unit == 'each'
        assert supply_line.product.suggested_department == 'PLU'
        assert supply_line.product.original_sku == 'B1-16A F'
        assert supply_line.product.specifications['connection_a'] == '3/8 in. Compression'
        assert supply_line.product.confidence >= 0.9
        towel = results[1]
        assert towel.product.clean_name == 'Multi-Purpose Microfiber Towel'
        assert towel.product.base_unit == 'pack'
        assert towel.product.pack_qty == 24
        assert towel.product.suggested_department == 'HDW'

    @pytest.mark.asyncio
    async def test_pipeline_without_llm_falls_back_to_rules(self):
        items = [{'name': '1/2 in PEX Pipe 100ft'}, {'name': 'Interior Latex Paint 5 Gal'}]
        results = await analyze_products(items, generate_text=None)
        assert len(results) == 2
        pipe = results[0]
        assert pipe.product.base_unit == 'foot'
        assert pipe.product.confidence == 0.3
        paint = results[1]
        assert paint.product.base_unit == 'gallon'

    @pytest.mark.asyncio
    async def test_pipeline_with_failing_llm_falls_back(self):

        def bad_llm(prompt, system=None):
            raise RuntimeError('LLM unavailable')
        items = [{'name': 'Widget'}]
        results = await analyze_products(items, generate_text=bad_llm)
        assert len(results) == 1
        assert results[0].product.confidence == 0.3

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self):
        results = await analyze_products([], generate_text=None)
        assert results == []

    @pytest.mark.asyncio
    async def test_vendor_match_wired(self):

        class FakeVI:
            sku_id = 'sku-123'
            id = 'vi-456'

        async def find_by_vendor_sku(vendor_id, vendor_sku):
            if vendor_sku == 'B1-16A F':
                return FakeVI()
            return None
        items = [{'name': 'BrassCraft supply line', 'original_sku': 'B1-16A F'}]

        def single_item_llm(prompt, system=None):
            return json.dumps([{'clean_name': 'Supply Line', 'original_sku': 'B1-16A F', 'base_unit': 'each', 'suggested_department': 'PLU', 'confidence': 0.9}])
        results = await analyze_products(items, generate_text=single_item_llm, vendor_id='vendor-1', find_by_vendor_sku=find_by_vendor_sku)
        assert results[0].matched_sku_id == 'sku-123'
        assert results[0].matched_vendor_item_id == 'vi-456'

    @pytest.mark.asyncio
    async def test_family_candidates_returned(self):

        async def search_families(query):
            return [{'id': 'fam-1', 'name': 'Faucet Supply Lines', 'similarity': 0.85}, {'id': 'fam-2', 'name': 'Braided Hoses', 'similarity': 0.6}]

        def single_item_llm(prompt, system=None):
            return json.dumps([{'clean_name': 'Faucet Supply Line', 'base_unit': 'each', 'suggested_department': 'PLU', 'confidence': 0.9}])
        items = [{'name': 'BrassCraft supply line'}]
        results = await analyze_products(items, generate_text=single_item_llm, search_families=search_families)
        assert len(results[0].family_candidates) == 2
        assert results[0].family_candidates[0].family_name == 'Faucet Supply Lines'
        assert results[0].family_candidates[0].similarity == 0.85

class TestRealWorldExamples:
    """Verify the batch pipeline handles the real receipt examples."""

    @pytest.fixture
    def home_depot_llm(self):

        def generate_text(prompt, system=None):
            return json.dumps([{'clean_name': 'Braided Polymer Faucet Supply Line', 'brand': 'BrassCraft', 'product_type': 'faucet supply line', 'specifications': {'connection_a': '3/8 in. Compression', 'connection_b': '1/2 in. FIP', 'length': '16 in.'}, 'base_unit': 'each', 'sell_uom': 'each', 'pack_qty': 1, 'suggested_department': 'PLU', 'variant_label': '16 in.', 'original_sku': 'B1-16A F', 'confidence': 0.95}, {'clean_name': 'Braided Polymer Faucet Supply Line', 'brand': 'BrassCraft', 'product_type': 'faucet supply line', 'specifications': {'connection_a': '3/8 in. Compression', 'connection_b': '1/2 in. FIP', 'length': '20 in.'}, 'base_unit': 'each', 'sell_uom': 'each', 'pack_qty': 1, 'suggested_department': 'PLU', 'variant_label': '20 in.', 'original_sku': 'B1-20A F', 'confidence': 0.95}, {'clean_name': 'Multi-Purpose Microfiber Towel', 'brand': 'HDX', 'product_type': 'cleaning towel', 'specifications': {'dimensions': '16 in. x 16 in.'}, 'base_unit': 'pack', 'sell_uom': 'pack', 'pack_qty': 24, 'suggested_department': 'HDW', 'variant_label': '24-Pack', 'original_sku': '2142099', 'confidence': 0.92}])
        return generate_text

    @pytest.mark.asyncio
    async def test_supply_line_not_misclassified_as_inch(self, home_depot_llm):
        items = [{'name': 'BrassCraft 3/8 in. Compression x 1/2 in. FIP x 16 in. Braided Polymer Faucet Supply Line'}, {'name': 'BrassCraft 3/8 in. Compression x 1/2 in. FIP x 20 in. Braided Polymer Faucet Supply Line'}, {'name': 'HDX 16 in. x 16 in. Multi-Purpose Microfiber Towel (24-Pack)'}]
        results = await analyze_products(items, generate_text=home_depot_llm)
        assert results[0].product.base_unit == 'each'
        assert results[0].product.pack_qty == 1
        assert results[0].product.suggested_department == 'PLU'
        assert results[1].product.base_unit == 'each'
        assert results[1].product.variant_label == '20 in.'
        assert results[2].product.base_unit == 'pack'
        assert results[2].product.pack_qty == 24
        assert results[2].product.suggested_department == 'HDW'

    @pytest.mark.asyncio
    async def test_smoke_detector_classified_correctly(self):

        def llm(prompt, system=None):
            return json.dumps([{'clean_name': 'Code One Hardwired Interconnectable Smoke and Carbon Monoxide Detector', 'brand': 'Kidde', 'product_type': 'smoke and CO detector', 'specifications': {'power': 'hardwired', 'backup': 'AA battery'}, 'base_unit': 'each', 'sell_uom': 'each', 'pack_qty': 1, 'suggested_department': 'ELE', 'variant_label': 'Hardwired', 'original_sku': '900-CUAR', 'confidence': 0.93}])
        items = [{'name': 'Kidde Code One Hardwired Interconnectable Smoke and Carbon Monoxide Detector, AA Battery Backup'}]
        results = await analyze_products(items, generate_text=llm)
        assert results[0].product.base_unit == 'each'
        assert results[0].product.suggested_department == 'ELE'
        assert results[0].product.brand == 'Kidde'
        assert results[0].product.original_sku == '900-CUAR'
