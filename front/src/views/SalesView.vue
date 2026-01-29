<template>
  <div>
    <h2>Продажа товаров</h2>
    <form @submit.prevent="handleSale">
      <div>
        <label>Товар:</label>
        <select v-model="saleForm.productId" @change="onProductChange" required>
          <option value="">Выберите товар</option>
          <option v-for="product in products" :key="product.id" :value="product.id">
            {{ product.name }} (остаток: {{ product.stock }}) {{ getGlassesPerBottleText(product) }}
          </option>
        </select>
      </div>

      <div>
        <label>Тип продажи:</label>
        <select v-model="saleForm.saleType" required>
          <option value="full">Полная продажа</option>
          <option value="glass" v-if="currentProductHasGlasses">Продажа бокалов</option>
        </select>
      </div>

      <div>
        <label>Количество:</label>
        <input 
          v-model.number="saleForm.quantity" 
          type="number" 
          min="0.01" 
          step="0.01" 
          :placeholder="getQuantityPlaceholder" 
          required 
        />
        <small v-if="currentProductHasGlasses && saleForm.saleType === 'glass'">
          1 бокал = {{ glassesPerBottle ? (1 / glassesPerBottle).toFixed(4) : '?' }} бутылки
        </small>
      </div>

      <button type="submit" :disabled="!canSubmit">
        Продать
      </button>
    </form>

    <div v-if="saleResult" class="result">
      <h3>Результат продажи:</h3>
      <p>{{ saleResult.message }}</p>
      <p><strong>Общая стоимость:</strong> {{ saleResult.totalCost }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Product } from '@/api/productApi'
import { productApi } from '@/api/productApi'

interface SaleForm {
  productId: number | null
  quantity: number
  saleType: 'full' | 'glass'
}

const saleForm = ref<SaleForm>({
  productId: null,
  quantity: 1,
  saleType: 'full'
})

const products = ref<Product[]>([])
const productTypes = ref<ProductType[]>([])
const saleResult = ref<SaleResponse | null>(null)
const glassesPerBottle = ref<number | null>(null)

// Helper to get attribute definitions for a product type
const productTypeAttributes = computed(() => {
  if (!saleForm.value.productId) return []
  const product = products.value.find(p => p.id === saleForm.value.productId)
  if (!product) return []

  const productType = productTypes.value.find(pt => pt.id === product.productTypeId)
  return productType ? productType.attributes : []
})

// Helper function to convert attributes array to object with codes as keys
const getAttributesAsObject = (productId: number) => {
  const product = products.value.find(p => p.id === productId);
  if (!product || !Array.isArray(product.attributes)) {
    return {};
  }

  // Need to get the product type to map attribute IDs to codes
  const productType = productTypes.value.find(pt => pt.id === product.productTypeId);
  if (!productType || !productType.attributes) {
    return {};
  }

  const attrObj: Record<string, any> = {};
  product.attributes.forEach(attr => {
    const attrDef = productType.attributes.find(def => def.id === attr.attributeDefinitionId);
    if (attrDef) {
      attrObj[attrDef.code] = attr.value;
    }
  });

  return attrObj;
};

const currentProductHasGlasses = computed(() => {
  if (!saleForm.value.productId) return false
  const attrObj = getAttributesAsObject(saleForm.value.productId);
  return attrObj.glassesPerBottle !== undefined && attrObj.glassesPerBottle !== null;
});

const canSubmit = computed(() => {
  return saleForm.value.productId !== null && 
         saleForm.value.quantity > 0 &&
         (!currentProductHasGlasses.value || saleForm.value.saleType !== 'glass' || glassesPerBottle.value !== null)
})

const getQuantityPlaceholder = computed(() => {
  if (saleForm.value.saleType === 'glass' && currentProductHasGlasses.value) {
    return 'Количество бокалов'
  }
  return 'Количество'
})

const getGlassesPerBottleText = (product: Product) => {
  if (Array.isArray(product.attributes)) {
    // Need to get the product type to map attribute IDs to codes
    const productType = productTypes.value.find(pt => pt.id === product.productTypeId);
    if (!productType || !productType.attributes) {
      return '';
    }

    const attrDef = productType.attributes.find(def => def.code === 'glasses_per_bottle');
    if (attrDef) {
      const attrValue = product.attributes.find(attr => attr.attributeDefinitionId === attrDef.id);
      if (attrValue && attrValue.value) {
        return `(бокалов в бутылке: ${attrValue.value})`;
      }
    }
  }
  return ''
}

const onProductChange = () => {
  if (saleForm.value.productId) {
    const product = products.value.find(p => p.id === saleForm.value.productId)
    if (Array.isArray(product.attributes)) {
      // Need to get the product type to map attribute IDs to codes
      const productType = productTypes.value.find(pt => pt.id === product.productTypeId);
      if (!productType || !productType.attributes) {
        glassesPerBottle.value = null;
        saleForm.value.saleType = 'full';
        return;
      }

      const attrDef = productType.attributes.find(def => def.code === 'glasses_per_bottle');
      if (attrDef) {
        const attrValue = product.attributes.find(attr => attr.attributeDefinitionId === attrDef.id);
        if (attrValue && attrValue.value) {
          glassesPerBottle.value = parseFloat(attrValue.value);
          if (!currentProductHasGlasses.value) {
            saleForm.value.saleType = 'full';
          }
          return;
        }
      }
    }

    glassesPerBottle.value = null;
    saleForm.value.saleType = 'full';
  }
}

const handleSale = async () => {
  try {
    const saleRequest: SaleRequest = {
      productId: saleForm.value.productId!,
      quantity: saleForm.value.quantity
    }

    let result: SaleResponse;
    if (saleForm.value.saleType === 'glass') {
      result = await productApi.sellWineGlass(saleRequest)
    } else {
      result = await productApi.sellProduct(saleRequest)
    }

    saleResult.value = result
    // Refresh products list
    loadProducts()
    // Reset form
    saleForm.value = { productId: null, quantity: 1, saleType: 'full' }
    glassesPerBottle.value = null
  } catch (error) {
    console.error('Ошибка при продаже:', error)
    alert(error instanceof Error ? error.message : 'Ошибка при продаже товара')
  }
}

const loadProducts = async () => {
  try {
    products.value = await productApi.getProducts()
  } catch (error) {
    console.error('Ошибка при загрузке товаров:', error)
  }
}

onMounted(async () => {
  await Promise.all([
    loadProducts(),
    loadProductTypes()
  ]);
})

const loadProductTypes = async () => {
  try {
    productTypes.value = await productApi.getProductTypes();
  } catch (error) {
    console.error('Ошибка при загрузке типов товаров:', error);
  }
}
</script>

<style scoped>
form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-width: 400px;
  margin-bottom: 2rem;
}

form > div {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.result {
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: #f5f5f5;
}
</style>