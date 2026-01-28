import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1/simple-catalog'
})

export interface Unit {
  id: number
  symbol: string
  name: string
}

export interface AttributeDefinition {
  id: number
  name: string
  code: string
  dataType: 'number' | 'boolean' | 'string'
  unitId?: number
  isRequired: boolean
}

export interface ProductType {
  id: number
  name: string
  isComposite: boolean
  attributes: AttributeDefinition[]
}

export interface ProductForm {
  productTypeId: number
  name: string
  unitCost: string              // ← строка, не number!
  stock: string                 // ← строка
  attributes: Record<string, any>
  components: Array<{
    componentProductId: number
    quantity: number
  }>
}

export interface Product {
  id: number
  product_type_id: number
  name: string
  stock: number
  unit_cost: number
  is_composite: boolean
  attributes: Record<string, any>
  components: Array<{ componentProductId: number; quantity: number }>
}

export const productApi = {
  async getProductTypes(): Promise<ProductType[]> {
    const res = await api.get<ProductType[]>('/product-types/')
    return res.data
  },

  async getProducts(): Promise<Product[]> {
    const res = await api.get<Product[]>('/products/')
    return res.data
  },

  async createProduct(data: ProductForm) {
    // First, we need to get the attribute definitions to map the values correctly
    const productType = await api.get(`/product-types/${data.productTypeId}`)
    const attributeDefs = productType.data.attributes

    // Convert attributes to the expected format
    const attributes = Object.entries(data.attributes).map(([code, value]) => {
      // Only include attributes that have values (not null/undefined)
      if (value === null || value === undefined) {
        return null;
      }

      const attrDef = attributeDefs.find((def: AttributeDefinition) => def.code === code)
      if (!attrDef) {
        throw new Error(`Attribute definition not found for code: ${code}`)
      }
      return {
        attribute_definition_id: attrDef.id,
        value
      }
    }).filter(Boolean); // Remove null entries

    const payload = {
      product_type_id: data.productTypeId,
      name: data.name,
      unit_cost: data.unitCost,
      stock: data.stock,
      attributes,
      components: data.components.map(c => ({ [c.componentProductId]: c.quantity }))
    }

    return api.post('/products/', payload)
  },

async updateProduct(id: number, data: ProductForm) {
  // 🔒 Валидация: productTypeId должен быть числом > 0
  if (!data.productTypeId || typeof data.productTypeId !== 'number' || data.productTypeId <= 0) {
    throw new Error('Invalid productTypeId')
  }

  // Загружаем тип товара для маппинга атрибутов
  const productType = await api.get(`/product-types/${data.productTypeId}`)
  const attributeDefs = productType.data.attributes

  // Преобразуем атрибуты
  const attributes = Object.entries(data.attributes)
    .map(([code, value]) => {
      if (value === null || value === undefined || value === '') return null

      const attrDef = attributeDefs.find((def: AttributeDefinition) => def.code === code)
      if (!attrDef) {
        console.warn(`Attribute definition not found for code: ${code}`)
        return null
      }

      return {
        attribute_definition_id: attrDef.id,
        value: String(value) // всегда строка!
      }
    })
    .filter(Boolean) as Array<{ attribute_definition_id: number; value: string }>

  // ✅ Правильный формат компонентов
  const components = (data.components || [])
    .filter(c => c.componentProductId > 0 && c.quantity > 0) // фильтруем пустые
    .map(c => ({
      component_product_id: c.componentProductId, // ← ключи как в API
      quantity: c.quantity
    }))

  const payload = {
    product_type_id: data.productTypeId,
    name: data.name,
    unit_cost: data.unitCost,   // строка, например "33.00"
    stock: data.stock,          // строка, например "44.000000"
    attributes,
    components
  }

  return api.put(`/products/${id}`, payload)
},

  async deleteProduct(id: number) {
    return api.delete(`/products/${id}`)
  },

  async getProduct(id: number): Promise<Product> {
    const res = await api.get<Product>(`/products/${id}`)
    return res.data
  }
}
