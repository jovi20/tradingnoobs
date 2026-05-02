type EntityWithId = {
    id: number
    public_id?: string | null
}

export function getEntityRouteId(entity: EntityWithId): string {
    return entity.public_id || String(entity.id)
}
