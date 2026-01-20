import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000'
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
  unitCost: number
  stock: number
  attributes: Record<string, any>
  components: Array<{ componentProductId: number; quantity: number }>
}

export const productApi = {
  async getProductTypes(): Promise<ProductType[]> {
    const res = await api.get('/product-types/')
    return res.data
  },

  async createProduct(data: ProductForm) {
    // Преобразуем атрибуты
    const attributes = Object.entries(data.attributes).map(([code, value]) => {
      const def = data.attributesDefinitions.find((d: any) => d.code === code)
      return {
        attribute_definition_id: def.id,
        value
      }
    })

    const payload = {
      product_type_id: data.productTypeId,
      name: data.name,
      unit_cost: data.unitCost,
      stock: data.stock,
      attributes,
      components: data.components.map(c => ({ [c.componentProductId]: c.quantity }))
    }

    return api.post('/products/', payload)
  }
}