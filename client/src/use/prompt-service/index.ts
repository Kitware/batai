import { createApp, App, inject } from 'vue';
import { createVuetify } from 'vuetify';
import Prompt from './Prompt.vue';

export interface PromptParams {
  title: string;
  text: string | string[];
  positiveButton?: string;
  negativeButton?: string;
  confirm?: boolean;
}

class PromptService {

  private app: App;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private component: any;

  constructor() {
    const app = createApp(Prompt);
    const Vuetify = createVuetify({});
    app.use(Vuetify);
    const div = document.createElement('div');
    document.body.appendChild(div);
    this.component = app.mount(div);
    this.app = app;
  }

  set(
    title: string,
    text: string | string[],
    positiveButton: string,
    negativeButton: string,
    confirm: boolean,
    resolve: (value: boolean) => unknown,
  ): void {
    this.component.title = title;
    this.component.text = text;
    this.component.positiveButton = positiveButton;
    this.component.negativeButton = negativeButton;
    this.component.confirm = confirm;
    this.component.value = null;
    this.component.functions.resolve = resolve;
    this.component.show = true;
  }

  show(params: PromptParams): Promise<boolean> {
    return new Promise((resolve) => {
      if (!this.component.show) {
        this.set(
          params.title,
          params.text,
          params.positiveButton ?? 'Confirm',
          params.negativeButton ?? 'Cancel',
          params.confirm ?? false,
          resolve,
        );
      }
    });
  }

  inputValue(params: PromptParams): Promise<boolean | number | string | null> {
    return new Promise((resolve) => {
      if (!this.component.show) {
        this.set(
          params.title,
          params.text,
          params.positiveButton ?? 'Confirm',
          params.negativeButton ?? 'Cancel',
          params.confirm ?? false,
          resolve,
        );
      }
    });
  }

  visible() {
    return this.component.show;
  }

  invisible() {
    return !this.component.show;
  }

  hide() {
    this.component.show = false;
  }
}

const PromptSymbol = Symbol('PromptService');

export function installPrompt(app: App) {
  const promptService = new PromptService();
  app.provide(PromptSymbol, promptService);
}

export function usePrompt() {
  const promptService = inject<PromptService>(PromptSymbol);
  if (!promptService) {
    throw new Error('PromptService not provided');
  }
  return {
    prompt: (params: PromptParams) => promptService.show(params),
    inputValue: (params: PromptParams) => promptService.inputValue(params),
    visible: () => promptService.visible(),
    invisible: () => promptService.invisible(),
    hide: () => promptService.hide(),
  };
}