import { ref, Ref } from 'vue';

const annotationState: Ref<AnnotationState> = ref('');

type AnnotationState = '' | 'editing' | 'creating';
export default function useState() {
    const setAnnotationState = (state: AnnotationState) => {
        annotationState.value = state;
    };
    return {
        annotationState,
        setAnnotationState,
    };
}

