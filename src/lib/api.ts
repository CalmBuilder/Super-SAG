import {invokePlatform} from './platform';
export const api=<T>(command:string,args?:Record<string,unknown>)=>invokePlatform<T>(command,args);
