// Desktop keeps 'sag.preview.legacy'; browser preferences use their own namespace.
import {appStorage} from './storage';

export function legacyPreview(){
 try{return appStorage.getItem('sag.preview.legacy')==='1'}catch{return false}
}
