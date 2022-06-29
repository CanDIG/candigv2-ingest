import mappings


def connect_variant(mapping):
    genomic_id = mappings.single_val({"GenomicID": mapping["1000 Genomes_ID"]})
    if genomic_id is None:
        return None
    return {"genomic_id": genomic_id}

def connect_code(mapping):
    return "code"
    
def connect_org(mapping):
    return "org"
    
def date(mapping):
    return "2022-04-05"
    
def language(mapping):
    return "English"
