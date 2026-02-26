import { computed, type Ref } from 'vue'

import type { Product } from '@/api/productApi'

type ProductListRef = Readonly<Ref<Product[]>>

interface ProductAutocompleteOptions {
  limit?: number
  formatOption?: (product: Product) => string
}

const defaultFormatProductOption = (product: Product): string => `${product.name} (id=${product.id})`

export const useProductAutocomplete = (
  products: ProductListRef,
  query: Ref<string>,
  options: ProductAutocompleteOptions = {}
) => {
  const limit = options.limit ?? 200
  const formatProductOption = options.formatOption ?? defaultFormatProductOption

  const productOptions = computed(() => {
    const normalizedQuery = query.value.trim().toLowerCase()
    if (!normalizedQuery) return products.value.slice(0, limit)
    return products.value.filter((product) => product.name.toLowerCase().includes(normalizedQuery)).slice(0, limit)
  })

  const parseProductIdFromQuery = (rawQuery: string): number => {
    const value = rawQuery.trim()
    if (!value) return 0

    const idFromOption = value.match(/\(id=(\d+)(?:[),]|$)/)
    if (idFromOption) return Number(idFromOption[1])

    const numericValue = Number(value)
    if (Number.isInteger(numericValue) && numericValue > 0) return numericValue

    const normalizedValue = value.toLowerCase()
    const exactByName = products.value.find((product) => product.name.toLowerCase() === normalizedValue)
    if (exactByName) return exactByName.id

    const partialMatches = products.value.filter((product) => product.name.toLowerCase().includes(normalizedValue))
    const firstMatch = partialMatches[0]
    return partialMatches.length === 1 && firstMatch ? firstMatch.id : 0
  }

  const syncQueryBySelectedProductId = (productId?: number | null): void => {
    if (!productId) {
      query.value = ''
      return
    }
    const found = products.value.find((product) => product.id === productId)
    query.value = found ? formatProductOption(found) : ''
  }

  return {
    productOptions,
    formatProductOption,
    parseProductIdFromQuery,
    syncQueryBySelectedProductId,
  }
}
