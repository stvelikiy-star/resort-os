import React from 'react';
import {fireEvent,render,waitFor} from '@testing-library/react-native';
import '../src/i18n';
import TaskDetail from '../app/task/[id]';
import {ThemeProvider} from '../src/theme/ThemeProvider';
import {ApiError,Task} from '../src/api/types';
let mockId='repair';
const row:Task={id:'repair',type:'MAINTENANCE',status:'IN_PROGRESS',priority:'NORMAL',title:'Repair',room_id:'room',room_code:'R-1',room_state:'TECH_BLOCK',assigned_to_id:'tech'};
const mockApi={mode:'LIVE',listTasks:jest.fn(async()=>[row,{...row,id:'repair-2'}]),completeMaintenance:jest.fn(),setTaskStatus:jest.fn()};
jest.mock('../src/state/session',()=>({useSession:()=>({api:mockApi,user:{id:'tech',role:'TECHNICIAN',module_permissions:['OPS']},hotel:{id:'hotel'},locale:'en',serverAuthMode:'single_property'})}));
jest.mock('expo-router',()=>({useLocalSearchParams:()=>({id:mockId}),useRouter:()=>({back:jest.fn()}),Redirect:()=>null}));
jest.mock('react-native-safe-area-context',()=>({useSafeAreaInsets:()=>({top:0,bottom:0,left:0,right:0})}));
const screen=()=> <ThemeProvider initial="light"><TaskDetail/></ThemeProvider>;
beforeEach(()=>{mockId='repair';mockApi.completeMaintenance.mockReset().mockResolvedValue({...row,status:'DONE',room_state:'DIRTY'});mockApi.setTaskStatus.mockClear();});
test('requires meaningful report and submits through report API, not raw status patch',async()=>{
 const view=await render(screen());await waitFor(()=>expect(view.getByTestId('task-finish')).toBeDisabled());
 await fireEvent.changeText(view.getByTestId('repair-summary'),'  Valve repaired  ');
 await fireEvent.press(view.getByTestId('task-finish'));
 await waitFor(()=>expect(view.getByTestId('repair-room-state')).toHaveTextContent('Room sent for cleaning'));
 expect(mockApi.completeMaintenance).toHaveBeenCalledWith('repair',{summary:'  Valve repaired  '});expect(mockApi.setTaskStatus).not.toHaveBeenCalled();
});
test('unknown result blocks a second report',async()=>{
 mockApi.completeMaintenance.mockRejectedValue(new Error('ack lost'));
 const view=await render(screen());await waitFor(()=>view.getByTestId('repair-summary'));
 await fireEvent.changeText(view.getByTestId('repair-summary'),'Valve repaired');await fireEvent.press(view.getByTestId('task-finish'));
 await waitFor(()=>expect(view.getByTestId('task-finish')).toBeDisabled());await fireEvent.press(view.getByTestId('task-finish'));
 expect(mockApi.completeMaintenance).toHaveBeenCalledTimes(1);expect(view.queryByTestId('repair-room-state')).toBeNull();
});
test('server denial never displays a completed room',async()=>{
 mockApi.completeMaintenance.mockRejectedValue(new ApiError('FORBIDDEN'));
 const view=await render(screen());await waitFor(()=>view.getByTestId('repair-summary'));
 await fireEvent.changeText(view.getByTestId('repair-summary'),'Valve repaired');await fireEvent.press(view.getByTestId('task-finish'));
 await waitFor(()=>expect(mockApi.completeMaintenance).toHaveBeenCalledTimes(1));expect(view.queryByTestId('repair-room-state')).toBeNull();
});
test('switching tasks does not carry a report into another task',async()=>{
 const view=await render(screen());await waitFor(()=>view.getByTestId('repair-summary'));
 await fireEvent.changeText(view.getByTestId('repair-summary'),'Report for old task');mockId='repair-2';await view.rerender(screen());
 await waitFor(()=>expect(view.getByTestId('repair-summary')).toHaveProp('value',''));expect(view.getByTestId('task-finish')).toBeDisabled();
});
